from __future__ import annotations

from pathlib import Path
from typing import Sequence
import argparse
import json

from .agent_runner import AgentProvider, run_agent
from .analysis import build_local_report
from .collector import collect_to_store
from .models import TopicConfig
from .report import write_json_report, write_markdown_report
from .store import EvidenceStore


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate-config":
        config = TopicConfig.from_file(Path(args.config))
        print(json.dumps({"ok": True, "topic": config.topic}, ensure_ascii=False))
        return 0
    if args.command == "collect":
        summary = collect_to_store(
            config_path=Path(args.config),
            db_path=Path(args.db),
            dry_run=bool(args.dry_run),
        )
        print(json.dumps(summary.__dict__, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "analyze-local":
        with EvidenceStore(Path(args.db)) as store:
            items = list(store.iter_items(topic=args.topic, limit=args.limit))
        report = build_local_report(
            items=items,
            topic=args.topic,
            max_evidence=int(args.max_evidence),
        )
        write_markdown_report(report, Path(args.output))
        if args.json_output:
            write_json_report(report, Path(args.json_output))
        print(json.dumps({"ok": True, "items": len(items), "output": args.output}, ensure_ascii=False))
        return 0
    if args.command == "export-jsonl":
        with EvidenceStore(Path(args.db)) as store:
            count = store.export_jsonl(
                output_path=Path(args.output),
                topic=args.topic,
                limit=args.limit,
            )
        print(json.dumps({"ok": True, "count": count, "output": args.output}, ensure_ascii=False))
        return 0
    if args.command == "agent":
        provider = parse_provider(args.provider)
        result = run_agent(
            provider=provider,
            input_path=Path(args.input),
            prompt_path=Path(args.prompt),
            schema_path=Path(args.schema),
            output_path=Path(args.output),
            dry_run=bool(args.dry_run),
            claude_bare=bool(args.claude_bare),
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "provider": result.provider,
                    "dry_run": result.dry_run,
                    "output": str(result.output_path),
                    "command": list(result.command),
                },
                ensure_ascii=False,
            )
        )
        return 0
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reddit-needs-researcher",
        description="Collect Reddit evidence and analyze user pain points.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-config")
    validate_parser.add_argument("--config", required=True)

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--config", required=True)
    collect_parser.add_argument("--db", required=True)
    collect_parser.add_argument("--dry-run", action="store_true")

    analyze_parser = subparsers.add_parser("analyze-local")
    analyze_parser.add_argument("--db", required=True)
    analyze_parser.add_argument("--topic")
    analyze_parser.add_argument("--output", required=True)
    analyze_parser.add_argument("--json-output")
    analyze_parser.add_argument("--limit", type=int)
    analyze_parser.add_argument("--max-evidence", type=int, default=50)

    export_parser = subparsers.add_parser("export-jsonl")
    export_parser.add_argument("--db", required=True)
    export_parser.add_argument("--topic")
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--limit", type=int)

    agent_parser = subparsers.add_parser("agent")
    agent_parser.add_argument("--provider", choices=("codex", "claude"), required=True)
    agent_parser.add_argument("--input", required=True)
    agent_parser.add_argument("--prompt", required=True)
    agent_parser.add_argument("--schema", required=True)
    agent_parser.add_argument("--output", required=True)
    agent_parser.add_argument("--dry-run", action="store_true")
    agent_parser.add_argument(
        "--claude-bare",
        action="store_true",
        help="Use Claude bare mode; requires explicit API-key based auth.",
    )
    return parser


def parse_provider(value: str) -> AgentProvider:
    if value == "codex" or value == "claude":
        return value
    raise ValueError(f"unsupported provider: {value}")


if __name__ == "__main__":
    raise SystemExit(main())

