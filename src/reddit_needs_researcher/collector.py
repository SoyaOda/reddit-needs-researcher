from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import JsonValue, SourceItem, TopicConfig
from .reddit_client import RedditClient
from .store import EvidenceStore


REDDIT_WEB_BASE_URL = "https://www.reddit.com"


@dataclass(frozen=True)
class CollectionSummary:
    topic: str
    planned_requests: int
    posts_seen: int
    comments_seen: int
    items_saved: int
    dry_run: bool


def collect_to_store(
    *,
    config_path: Path,
    db_path: Path,
    dry_run: bool,
) -> CollectionSummary:
    config = TopicConfig.from_file(config_path)
    planned_requests = estimate_planned_requests(config)
    if dry_run:
        return CollectionSummary(
            topic=config.topic,
            planned_requests=planned_requests,
            posts_seen=0,
            comments_seen=0,
            items_saved=0,
            dry_run=True,
        )

    client = RedditClient.from_env(
        min_seconds_between_requests=config.min_seconds_between_requests,
    )
    posts: list[SourceItem] = []
    comments: list[SourceItem] = []
    seen_post_ids: set[str] = set()

    for subreddit in config.subreddits:
        for query in config.queries:
            for sort in config.search_sorts:
                for time_filter in config.time_filters:
                    payload = client.search_subreddit(
                        subreddit=subreddit,
                        query=query,
                        sort=sort,
                        time_filter=time_filter,
                        limit=config.post_limit_per_query,
                    )
                    fetched_at = current_timestamp()
                    batch_posts = parse_listing_posts(
                        payload=payload,
                        topic=config.topic,
                        query=query,
                        fetched_at=fetched_at,
                        store_author=config.store_author,
                    )
                    for post in batch_posts:
                        if post.fullname in seen_post_ids:
                            continue
                        seen_post_ids.add(post.fullname)
                        posts.append(post)
                        if config.comment_limit_per_post > 0:
                            comments_payload = client.comments(
                                subreddit=post.subreddit,
                                submission_id=post.fullname.removeprefix("t3_"),
                                limit=config.comment_limit_per_post,
                                sort=config.comment_sort,
                                depth=config.comment_depth,
                            )
                            comments.extend(
                                parse_comments_response(
                                    payload=comments_payload,
                                    topic=config.topic,
                                    query=query,
                                    fetched_at=current_timestamp(),
                                    store_author=config.store_author,
                                )
                            )

    with EvidenceStore(db_path) as store:
        saved = store.upsert_items([*posts, *comments])
    return CollectionSummary(
        topic=config.topic,
        planned_requests=planned_requests,
        posts_seen=len(posts),
        comments_seen=len(comments),
        items_saved=saved,
        dry_run=False,
    )


def estimate_planned_requests(config: TopicConfig) -> int:
    search_requests = (
        len(config.subreddits)
        * len(config.queries)
        * len(config.search_sorts)
        * len(config.time_filters)
    )
    max_comment_requests = search_requests * config.post_limit_per_query
    if config.comment_limit_per_post <= 0:
        max_comment_requests = 0
    return search_requests + max_comment_requests


def parse_listing_posts(
    *,
    payload: dict[str, JsonValue],
    topic: str,
    query: str | None,
    fetched_at: str,
    store_author: bool,
) -> list[SourceItem]:
    children = get_listing_children(payload)
    items: list[SourceItem] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        if child.get("kind") != "t3":
            continue
        data = child.get("data")
        if not isinstance(data, dict):
            continue
        item = post_from_data(
            data=data,
            topic=topic,
            query=query,
            fetched_at=fetched_at,
            store_author=store_author,
        )
        if item is not None:
            items.append(item)
    return items


def parse_comments_response(
    *,
    payload: list[JsonValue],
    topic: str,
    query: str | None,
    fetched_at: str,
    store_author: bool,
) -> list[SourceItem]:
    if len(payload) < 2:
        return []
    comments_listing = payload[1]
    if not isinstance(comments_listing, dict):
        return []
    children = get_listing_children(comments_listing)
    comments: list[SourceItem] = []
    for child in children:
        comments.extend(
            flatten_comment_child(
                child=child,
                topic=topic,
                query=query,
                fetched_at=fetched_at,
                store_author=store_author,
            )
        )
    return comments


def flatten_comment_child(
    *,
    child: JsonValue,
    topic: str,
    query: str | None,
    fetched_at: str,
    store_author: bool,
) -> list[SourceItem]:
    if not isinstance(child, dict) or child.get("kind") != "t1":
        return []
    data = child.get("data")
    if not isinstance(data, dict):
        return []
    comment = comment_from_data(
        data=data,
        topic=topic,
        query=query,
        fetched_at=fetched_at,
        store_author=store_author,
    )
    comments = [comment] if comment is not None else []
    replies = data.get("replies")
    if isinstance(replies, dict):
        for reply_child in get_listing_children(replies):
            comments.extend(
                flatten_comment_child(
                    child=reply_child,
                    topic=topic,
                    query=query,
                    fetched_at=fetched_at,
                    store_author=store_author,
                )
            )
    return comments


def get_listing_children(payload: dict[str, JsonValue]) -> list[JsonValue]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    children = data.get("children")
    if not isinstance(children, list):
        return []
    return children


def post_from_data(
    *,
    data: dict[str, JsonValue],
    topic: str,
    query: str | None,
    fetched_at: str,
    store_author: bool,
) -> SourceItem | None:
    fullname = get_string(data, "name")
    if fullname is None:
        return None
    permalink = get_string(data, "permalink") or ""
    return SourceItem(
        topic=topic,
        fullname=fullname,
        kind="post",
        subreddit=get_string(data, "subreddit") or "",
        title=get_string(data, "title") or "",
        body=get_string(data, "selftext") or "",
        author=(get_string(data, "author") if store_author else None),
        score=get_int(data, "score"),
        comment_count=get_int(data, "num_comments"),
        created_utc=get_float(data, "created_utc"),
        permalink=permalink,
        url=get_string(data, "url"),
        parent_fullname=None,
        query=query,
        fetched_at=fetched_at,
        raw=data,
    )


def comment_from_data(
    *,
    data: dict[str, JsonValue],
    topic: str,
    query: str | None,
    fetched_at: str,
    store_author: bool,
) -> SourceItem | None:
    fullname = get_string(data, "name")
    if fullname is None:
        return None
    permalink = get_string(data, "permalink") or ""
    return SourceItem(
        topic=topic,
        fullname=fullname,
        kind="comment",
        subreddit=get_string(data, "subreddit") or "",
        title="",
        body=get_string(data, "body") or "",
        author=(get_string(data, "author") if store_author else None),
        score=get_int(data, "score"),
        comment_count=0,
        created_utc=get_float(data, "created_utc"),
        permalink=permalink,
        url=f"{REDDIT_WEB_BASE_URL}{permalink}" if permalink else None,
        parent_fullname=get_string(data, "parent_id"),
        query=query,
        fetched_at=fetched_at,
        raw=data,
    )


def get_string(data: dict[str, JsonValue], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def get_int(data: dict[str, JsonValue], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def get_float(data: dict[str, JsonValue], key: str) -> float:
    value = data.get(key)
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def count_items(items: Iterable[SourceItem]) -> int:
    return sum(1 for _item in items)

