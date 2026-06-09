from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from reddit_needs_researcher.models import TopicConfig, SourceItem
from reddit_needs_researcher.store import EvidenceStore


class ConfigAndStoreTests(unittest.TestCase):
    def test_topic_config_parses_required_fields(self) -> None:
        config = TopicConfig.from_mapping(
            {
                "topic": "example",
                "subreddits": ["a", "b"],
                "queries": ["I wish"],
                "search_sorts": ["relevance"],
                "time_filters": ["month"],
                "post_limit_per_query": 10,
                "comment_limit_per_post": 5,
                "comment_sort": "confidence",
                "comment_depth": 3,
                "min_seconds_between_requests": 1.0,
                "store_author": False,
            }
        )
        self.assertEqual(config.topic, "example")
        self.assertEqual(config.subreddits, ("a", "b"))

    def test_store_upserts_and_exports_jsonl(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "evidence.sqlite"
            jsonl_path = Path(temp_dir) / "evidence.jsonl"
            item = make_item()
            with EvidenceStore(db_path) as store:
                self.assertEqual(store.upsert_items([item]), 1)
                self.assertEqual(store.upsert_items([item]), 1)
                self.assertEqual(store.count_items(topic="example"), 1)
                exported = store.export_jsonl(output_path=jsonl_path, topic="example")
            self.assertEqual(exported, 1)
            self.assertIn('"fullname": "t3_abc"', jsonl_path.read_text(encoding="utf-8"))


def make_item() -> SourceItem:
    return SourceItem(
        topic="example",
        fullname="t3_abc",
        kind="post",
        subreddit="example",
        title="Need app",
        body="I wish tracking was easier.",
        author=None,
        score=12,
        comment_count=3,
        created_utc=datetime.now(timezone.utc).timestamp(),
        permalink="/r/example/comments/abc/need_app/",
        url="https://www.reddit.com/r/example/comments/abc/need_app/",
        parent_fullname=None,
        query="wish app",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        raw={"name": "t3_abc"},
    )


if __name__ == "__main__":
    unittest.main()

