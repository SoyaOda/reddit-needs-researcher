from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import log1p
import re

from .models import JsonValue, SourceItem


MAX_EXCERPT_CHARS = 220
RECENCY_HALF_LIFE_DAYS = 180.0

SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "explicit_wish": (
        r"\bi wish\b",
        r"\bwould love\b",
        r"\bif only\b",
        r"\bi need\b",
    ),
    "friction": (
        r"\bfrustrat(?:ed|ing|ion)\b",
        r"\bannoy(?:ed|ing|ance)\b",
        r"\bhate\b",
        r"\btoo much work\b",
        r"\bhard to\b",
        r"\bstruggl(?:e|ing)\b",
        r"\bcan't\b",
        r"\bcannot\b",
    ),
    "seeking_solution": (
        r"\bdoes anyone know\b",
        r"\bany recommendations\b",
        r"\brecommend(?:ation)?\b",
        r"\blooking for\b",
        r"\bhow do i\b",
    ),
    "switching": (
        r"\balternative to\b",
        r"\breplace\b",
        r"\bswitch(?:ed|ing)?\b",
        r"\bbetter than\b",
    ),
    "cost": (
        r"\btoo expensive\b",
        r"\bpaywall\b",
        r"\bsubscription\b",
        r"\bprice\b",
        r"\bfree version\b",
    ),
    "trust_quality": (
        r"\binaccurate\b",
        r"\bunreliable\b",
        r"\bbug(?:gy|s)?\b",
        r"\bprivacy\b",
        r"\bads\b",
        r"\bsync\b",
    ),
}

COMPILED_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    name: tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
    for name, patterns in SIGNAL_PATTERNS.items()
}


@dataclass(frozen=True)
class ScoredEvidence:
    item: SourceItem
    score: float
    signals: tuple[str, ...]
    excerpt: str


def build_local_report(
    *,
    items: list[SourceItem],
    topic: str | None,
    max_evidence: int,
) -> dict[str, JsonValue]:
    scored = [score_evidence(item) for item in items]
    scored = [entry for entry in scored if entry.signals]
    scored.sort(key=lambda entry: entry.score, reverse=True)
    selected = scored[:max_evidence]
    clusters = cluster_evidence(selected)
    return {
        "topic": topic or infer_topic(items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items_scanned": len(items),
        "signal_items": len(scored),
        "top_evidence": [scored_evidence_to_json(entry) for entry in selected],
        "signal_clusters": clusters,
    }


def score_evidence(item: SourceItem) -> ScoredEvidence:
    text = item.text
    signals = detect_signals(text)
    signal_score = float(len(signals) * 5)
    engagement_score = log1p(max(item.score, 0)) + log1p(max(item.comment_count, 0))
    recency_score = recency_weight(item.created_utc)
    question_bonus = 2.0 if "?" in text else 0.0
    comment_bonus = 1.0 if item.kind == "comment" else 0.0
    score = signal_score + engagement_score + recency_score + question_bonus + comment_bonus
    return ScoredEvidence(
        item=item,
        score=round(score, 3),
        signals=signals,
        excerpt=make_excerpt(text),
    )


def detect_signals(text: str) -> tuple[str, ...]:
    matched: list[str] = []
    for name, patterns in COMPILED_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            matched.append(name)
    return tuple(matched)


def recency_weight(created_utc: float) -> float:
    if created_utc <= 0:
        return 0.0
    now = datetime.now(timezone.utc).timestamp()
    age_days = max((now - created_utc) / 86_400.0, 0.0)
    return max(0.0, 3.0 * (1.0 - min(age_days / RECENCY_HALF_LIFE_DAYS, 1.0)))


def make_excerpt(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= MAX_EXCERPT_CHARS:
        return normalized
    return f"{normalized[:MAX_EXCERPT_CHARS].rstrip()}..."


def cluster_evidence(scored: list[ScoredEvidence]) -> list[JsonValue]:
    grouped: dict[str, list[ScoredEvidence]] = defaultdict(list)
    for entry in scored:
        for signal in entry.signals:
            grouped[signal].append(entry)
    clusters: list[JsonValue] = []
    for signal, entries in sorted(grouped.items(), key=lambda pair: len(pair[1]), reverse=True):
        evidence_ids = [entry.item.fullname for entry in entries[:10]]
        subreddits = sorted({entry.item.subreddit for entry in entries if entry.item.subreddit})
        clusters.append(
            {
                "signal": signal,
                "count": len(entries),
                "subreddits": subreddits,
                "evidence_ids": evidence_ids,
            }
        )
    return clusters


def scored_evidence_to_json(entry: ScoredEvidence) -> dict[str, JsonValue]:
    return {
        "fullname": entry.item.fullname,
        "kind": entry.item.kind,
        "subreddit": entry.item.subreddit,
        "score": entry.score,
        "signals": list(entry.signals),
        "title": entry.item.title,
        "excerpt": entry.excerpt,
        "permalink": entry.item.permalink,
        "query": entry.item.query,
        "created_utc": entry.item.created_utc,
        "reddit_score": entry.item.score,
        "comment_count": entry.item.comment_count,
    }


def infer_topic(items: list[SourceItem]) -> str:
    for item in items:
        if item.topic:
            return item.topic
    return "unknown"

