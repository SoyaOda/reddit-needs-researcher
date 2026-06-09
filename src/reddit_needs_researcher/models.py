from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias
import json


JsonValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)

ItemKind = Literal["post", "comment"]
SearchSort = Literal["relevance", "hot", "top", "new", "comments"]
TimeFilter = Literal["hour", "day", "week", "month", "year", "all"]

DEFAULT_COMMENT_DEPTH = 4
DEFAULT_MIN_SECONDS_BETWEEN_REQUESTS = 1.0


@dataclass(frozen=True)
class TopicConfig:
    topic: str
    subreddits: tuple[str, ...]
    queries: tuple[str, ...]
    search_sorts: tuple[SearchSort, ...]
    time_filters: tuple[TimeFilter, ...]
    post_limit_per_query: int
    comment_limit_per_post: int
    comment_sort: str
    comment_depth: int
    min_seconds_between_requests: float
    store_author: bool

    @classmethod
    def from_file(cls, path: Path) -> "TopicConfig":
        with path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, dict):
            raise ValueError("config root must be an object")
        return cls.from_mapping(loaded)

    @classmethod
    def from_mapping(cls, value: dict[str, JsonValue]) -> "TopicConfig":
        topic = require_string(value, "topic")
        subreddits = require_string_tuple(value, "subreddits")
        queries = require_string_tuple(value, "queries")
        search_sorts = parse_search_sorts(value.get("search_sorts"))
        time_filters = parse_time_filters(value.get("time_filters"))
        post_limit = require_int(value, "post_limit_per_query", minimum=1, maximum=100)
        comment_limit = require_int(value, "comment_limit_per_post", minimum=0, maximum=500)
        comment_sort = optional_string(value, "comment_sort", default="confidence")
        comment_depth = require_int(
            value,
            "comment_depth",
            minimum=1,
            maximum=10,
            default=DEFAULT_COMMENT_DEPTH,
        )
        min_interval = require_float(
            value,
            "min_seconds_between_requests",
            minimum=0.1,
            default=DEFAULT_MIN_SECONDS_BETWEEN_REQUESTS,
        )
        store_author = require_bool(value, "store_author", default=False)
        return cls(
            topic=topic,
            subreddits=subreddits,
            queries=queries,
            search_sorts=search_sorts,
            time_filters=time_filters,
            post_limit_per_query=post_limit,
            comment_limit_per_post=comment_limit,
            comment_sort=comment_sort,
            comment_depth=comment_depth,
            min_seconds_between_requests=min_interval,
            store_author=store_author,
        )


@dataclass(frozen=True)
class SourceItem:
    topic: str
    fullname: str
    kind: ItemKind
    subreddit: str
    title: str
    body: str
    author: str | None
    score: int
    comment_count: int
    created_utc: float
    permalink: str
    url: str | None
    parent_fullname: str | None
    query: str | None
    fetched_at: str
    raw: dict[str, JsonValue]

    @property
    def text(self) -> str:
        parts = [self.title.strip(), self.body.strip()]
        return "\n".join(part for part in parts if part)

    def to_json_record(self) -> dict[str, JsonValue]:
        return {
            "topic": self.topic,
            "fullname": self.fullname,
            "kind": self.kind,
            "subreddit": self.subreddit,
            "title": self.title,
            "body": self.body,
            "author": self.author,
            "score": self.score,
            "comment_count": self.comment_count,
            "created_utc": self.created_utc,
            "permalink": self.permalink,
            "url": self.url,
            "parent_fullname": self.parent_fullname,
            "query": self.query,
            "fetched_at": self.fetched_at,
        }


def require_string(value: dict[str, JsonValue], key: str) -> str:
    raw_value = value.get(key)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return raw_value.strip()


def optional_string(value: dict[str, JsonValue], key: str, default: str) -> str:
    raw_value = value.get(key, default)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return raw_value.strip()


def require_string_tuple(value: dict[str, JsonValue], key: str) -> tuple[str, ...]:
    raw_value = value.get(key)
    if not isinstance(raw_value, list) or not raw_value:
        raise ValueError(f"{key} must be a non-empty string array")
    items: list[str] = []
    for entry in raw_value:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError(f"{key} must contain only non-empty strings")
        items.append(entry.strip())
    return tuple(items)


def require_int(
    value: dict[str, JsonValue],
    key: str,
    *,
    minimum: int,
    maximum: int | None = None,
    default: int | None = None,
) -> int:
    raw_value = value.get(key, default)
    if not isinstance(raw_value, int):
        raise ValueError(f"{key} must be an integer")
    if raw_value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    if maximum is not None and raw_value > maximum:
        raise ValueError(f"{key} must be <= {maximum}")
    return raw_value


def require_float(
    value: dict[str, JsonValue],
    key: str,
    *,
    minimum: float,
    default: float,
) -> float:
    raw_value = value.get(key, default)
    if not isinstance(raw_value, int | float):
        raise ValueError(f"{key} must be a number")
    number = float(raw_value)
    if number < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    return number


def require_bool(value: dict[str, JsonValue], key: str, *, default: bool) -> bool:
    raw_value = value.get(key, default)
    if not isinstance(raw_value, bool):
        raise ValueError(f"{key} must be a boolean")
    return raw_value


def parse_search_sorts(value: JsonValue) -> tuple[SearchSort, ...]:
    allowed: set[str] = {"relevance", "hot", "top", "new", "comments"}
    return parse_literal_tuple(value, "search_sorts", allowed)  # type: ignore[return-value]


def parse_time_filters(value: JsonValue) -> tuple[TimeFilter, ...]:
    allowed: set[str] = {"hour", "day", "week", "month", "year", "all"}
    return parse_literal_tuple(value, "time_filters", allowed)  # type: ignore[return-value]


def parse_literal_tuple(
    value: JsonValue,
    key: str,
    allowed: set[str],
) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{key} must be a non-empty string array")
    items: list[str] = []
    for entry in value:
        if not isinstance(entry, str):
            raise ValueError(f"{key} must contain only strings")
        normalized = entry.strip()
        if normalized not in allowed:
            joined = ", ".join(sorted(allowed))
            raise ValueError(f"{key} contains unsupported value {normalized!r}; use one of {joined}")
        items.append(normalized)
    return tuple(items)

