from __future__ import annotations

from pathlib import Path
import json

from .models import JsonValue


def write_json_report(report: dict[str, JsonValue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")


def write_markdown_report(report: dict[str, JsonValue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Local Reddit Needs Report: {report.get('topic', 'unknown')}")
    lines.append("")
    lines.append(f"- Generated at: `{report.get('generated_at', '')}`")
    lines.append(f"- Items scanned: `{report.get('items_scanned', 0)}`")
    lines.append(f"- Signal items: `{report.get('signal_items', 0)}`")
    lines.append("")
    lines.append("## Signal Clusters")
    lines.append("")
    clusters = report.get("signal_clusters")
    if isinstance(clusters, list):
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            signal = cluster.get("signal", "")
            count = cluster.get("count", 0)
            subreddits = cluster.get("subreddits", [])
            subreddit_text = ", ".join(str(item) for item in subreddits) if isinstance(subreddits, list) else ""
            lines.append(f"- `{signal}`: {count} items ({subreddit_text})")
    lines.append("")
    lines.append("## Top Evidence")
    lines.append("")
    evidence = report.get("top_evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            fullname = item.get("fullname", "")
            subreddit = item.get("subreddit", "")
            score = item.get("score", "")
            title = item.get("title", "")
            excerpt = item.get("excerpt", "")
            permalink = item.get("permalink", "")
            lines.append(f"### `{fullname}` r/{subreddit} score={score}")
            if title:
                lines.append(f"- Title: {title}")
            if excerpt:
                lines.append(f"- Excerpt: {excerpt}")
            if permalink:
                lines.append(f"- Permalink: https://www.reddit.com{permalink}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")

