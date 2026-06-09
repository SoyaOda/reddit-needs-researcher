#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"


def main() -> int:
    sys.path.insert(0, str(SRC_DIR))
    from reddit_needs_researcher.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())

