from __future__ import annotations

from datetime import datetime, timezone
import unittest

from reddit_needs_researcher.analysis import detect_signals, score_evidence
from reddit_needs_researcher.models import SourceItem


class AnalysisTests(unittest.TestCase):
    def test_detects_multiple_community_support_signals(self) -> None:
        text = "New here and confused about the rules. Where can I find the FAQ or weekly thread?"
        signals = detect_signals(text)
        self.assertIn("onboarding_friction", signals)
        self.assertIn("rule_confusion", signals)
        self.assertIn("repeated_question", signals)
        self.assertIn("faq_gap", signals)

    def test_scores_signal_item_above_neutral_item(self) -> None:
        now = datetime.now(timezone.utc).timestamp()
        signal_item = make_item(
            fullname="t3_signal",
            body="Does anyone know where the wiki is? I am new here and confused about the rules.",
            created_utc=now,
        )
        neutral_item = make_item(
            fullname="t3_neutral",
            body="Here is my weekly update.",
            created_utc=now,
        )
        self.assertGreater(score_evidence(signal_item).score, score_evidence(neutral_item).score)


def make_item(*, fullname: str, body: str, created_utc: float) -> SourceItem:
    return SourceItem(
        topic="test",
        fullname=fullname,
        kind="post",
        subreddit="testsub",
        title="",
        body=body,
        author=None,
        score=1,
        comment_count=0,
        created_utc=created_utc,
        permalink=f"/r/testsub/comments/{fullname}/",
        url=None,
        parent_fullname=None,
        query="test",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        raw={},
    )


if __name__ == "__main__":
    unittest.main()
