from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import os
import subprocess


AgentProvider = Literal["codex", "claude"]
DEFAULT_CODEX_MODEL = ""
DEFAULT_CLAUDE_MAX_TURNS = "3"


@dataclass(frozen=True)
class AgentRunResult:
    provider: AgentProvider
    command: tuple[str, ...]
    output_path: Path
    dry_run: bool
    return_code: int


def run_agent(
    *,
    provider: AgentProvider,
    input_path: Path,
    prompt_path: Path,
    schema_path: Path,
    output_path: Path,
    dry_run: bool,
    claude_bare: bool,
) -> AgentRunResult:
    prompt = prompt_path.read_text(encoding="utf-8")
    evidence = input_path.read_text(encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if provider == "codex":
        command = build_codex_command(prompt=prompt, schema_path=schema_path, output_path=output_path)
        stdin_text = evidence
    elif provider == "claude":
        command = build_claude_command(
            prompt=prompt,
            schema_path=schema_path,
            claude_bare=claude_bare,
        )
        stdin_text = evidence
    else:
        raise ValueError(f"unsupported provider: {provider}")

    if dry_run:
        return AgentRunResult(
            provider=provider,
            command=tuple(command),
            output_path=output_path,
            dry_run=True,
            return_code=0,
        )

    completed = subprocess.run(
        command,
        input=stdin_text,
        text=True,
        capture_output=True,
        check=False,
        env=sanitized_environment(),
    )
    if provider == "claude":
        output_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        stderr_path = output_path.with_suffix(f"{output_path.suffix}.stderr")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        raise RuntimeError(
            f"{provider} agent failed with exit code {completed.returncode}; stderr saved to {stderr_path}"
        )
    return AgentRunResult(
        provider=provider,
        command=tuple(command),
        output_path=output_path,
        dry_run=False,
        return_code=completed.returncode,
    )


def build_codex_command(*, prompt: str, schema_path: Path, output_path: Path) -> list[str]:
    return [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        prompt,
    ]


def build_claude_command(*, prompt: str, schema_path: Path, claude_bare: bool) -> list[str]:
    schema = schema_path.read_text(encoding="utf-8")
    command = [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        schema,
        "--max-turns",
        DEFAULT_CLAUDE_MAX_TURNS,
        "--no-session-persistence",
        "--tools",
        "",
    ]
    if claude_bare:
        command.insert(1, "--bare")
    command.append(prompt)
    return command


def sanitized_environment() -> dict[str, str]:
    blocked_prefixes = ("REDDIT_",)
    blocked_exact = {
        "PRAW_CLIENT_SECRET",
        "PRAW_PASSWORD",
    }
    cleaned: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith(blocked_prefixes):
            continue
        if key in blocked_exact:
            continue
        cleaned[key] = value
    return cleaned

