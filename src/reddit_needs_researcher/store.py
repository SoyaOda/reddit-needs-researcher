from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
import json
import sqlite3

from .models import JsonValue, SourceItem


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    fullname TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    kind TEXT NOT NULL,
    subreddit TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    author TEXT,
    score INTEGER NOT NULL,
    comment_count INTEGER NOT NULL,
    created_utc REAL NOT NULL,
    permalink TEXT NOT NULL,
    url TEXT,
    parent_fullname TEXT,
    query TEXT,
    fetched_at TEXT NOT NULL,
    raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_topic ON items(topic);
CREATE INDEX IF NOT EXISTS idx_items_subreddit ON items(subreddit);
CREATE INDEX IF NOT EXISTS idx_items_kind ON items(kind);
CREATE INDEX IF NOT EXISTS idx_items_created_utc ON items(created_utc);
"""


class EvidenceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA_SQL)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "EvidenceStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def upsert_items(self, items: Sequence[SourceItem]) -> int:
        rows = [source_item_to_row(item) for item in items]
        if not rows:
            return 0
        self._connection.executemany(
            """
            INSERT INTO items (
                fullname,
                topic,
                kind,
                subreddit,
                title,
                body,
                author,
                score,
                comment_count,
                created_utc,
                permalink,
                url,
                parent_fullname,
                query,
                fetched_at,
                raw_json
            ) VALUES (
                :fullname,
                :topic,
                :kind,
                :subreddit,
                :title,
                :body,
                :author,
                :score,
                :comment_count,
                :created_utc,
                :permalink,
                :url,
                :parent_fullname,
                :query,
                :fetched_at,
                :raw_json
            )
            ON CONFLICT(fullname) DO UPDATE SET
                topic = excluded.topic,
                kind = excluded.kind,
                subreddit = excluded.subreddit,
                title = excluded.title,
                body = excluded.body,
                author = excluded.author,
                score = excluded.score,
                comment_count = excluded.comment_count,
                created_utc = excluded.created_utc,
                permalink = excluded.permalink,
                url = excluded.url,
                parent_fullname = excluded.parent_fullname,
                query = COALESCE(items.query, excluded.query),
                fetched_at = excluded.fetched_at,
                raw_json = excluded.raw_json
            """,
            rows,
        )
        self._connection.commit()
        return len(rows)

    def iter_items(self, *, topic: str | None = None, limit: int | None = None) -> Iterator[SourceItem]:
        parameters: list[str | int] = []
        where_clause = ""
        if topic is not None:
            where_clause = "WHERE topic = ?"
            parameters.append(topic)
        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            parameters.append(limit)
        cursor = self._connection.execute(
            f"""
            SELECT *
            FROM items
            {where_clause}
            ORDER BY created_utc DESC, fullname ASC
            {limit_clause}
            """,
            parameters,
        )
        for row in cursor:
            yield row_to_source_item(row)

    def count_items(self, *, topic: str | None = None) -> int:
        if topic is None:
            cursor = self._connection.execute("SELECT COUNT(*) FROM items")
        else:
            cursor = self._connection.execute("SELECT COUNT(*) FROM items WHERE topic = ?", (topic,))
        value = cursor.fetchone()[0]
        if not isinstance(value, int):
            raise RuntimeError("sqlite COUNT result was not an integer")
        return value

    def export_jsonl(self, *, output_path: Path, topic: str | None = None, limit: int | None = None) -> int:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with output_path.open("w", encoding="utf-8") as file:
            for item in self.iter_items(topic=topic, limit=limit):
                file.write(json.dumps(item.to_json_record(), ensure_ascii=False, sort_keys=True))
                file.write("\n")
                count += 1
        return count


def source_item_to_row(item: SourceItem) -> dict[str, str | int | float | None]:
    return {
        "fullname": item.fullname,
        "topic": item.topic,
        "kind": item.kind,
        "subreddit": item.subreddit,
        "title": item.title,
        "body": item.body,
        "author": item.author,
        "score": item.score,
        "comment_count": item.comment_count,
        "created_utc": item.created_utc,
        "permalink": item.permalink,
        "url": item.url,
        "parent_fullname": item.parent_fullname,
        "query": item.query,
        "fetched_at": item.fetched_at,
        "raw_json": json.dumps(item.raw, ensure_ascii=False, sort_keys=True),
    }


def row_to_source_item(row: sqlite3.Row) -> SourceItem:
    raw_loaded = json.loads(str(row["raw_json"]))
    raw = normalize_loaded_json(raw_loaded)
    return SourceItem(
        topic=str(row["topic"]),
        fullname=str(row["fullname"]),
        kind=parse_kind(str(row["kind"])),
        subreddit=str(row["subreddit"]),
        title=str(row["title"]),
        body=str(row["body"]),
        author=parse_optional_string(row["author"]),
        score=int(row["score"]),
        comment_count=int(row["comment_count"]),
        created_utc=float(row["created_utc"]),
        permalink=str(row["permalink"]),
        url=parse_optional_string(row["url"]),
        parent_fullname=parse_optional_string(row["parent_fullname"]),
        query=parse_optional_string(row["query"]),
        fetched_at=str(row["fetched_at"]),
        raw=raw,
    )


def parse_kind(value: str) -> str:
    if value not in {"post", "comment"}:
        raise ValueError(f"unsupported item kind: {value}")
    return value


def parse_optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def normalize_loaded_json(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, JsonValue] = {}
    for key, item in value.items():
        if isinstance(key, str):
            normalized[key] = normalize_json_value(item)
    return normalized


def normalize_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if isinstance(key, str):
                normalized[key] = normalize_json_value(item)
        return normalized
    return str(value)

