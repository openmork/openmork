#!/usr/bin/env python3
"""Simple guard: detect bare/silent except-pass blocks in cli.py and core/*.py."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EXCEPT_PASS_RE = re.compile(r"except(?:\s+(?:Exception|BaseException))?\s*:\s*\n\s*pass\b", re.MULTILINE)


def scan_paths(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in EXCEPT_PASS_RE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"{p}:{line}")
    return hits


def collect_default_targets(repo_root: Path) -> list[Path]:
    targets = [repo_root / "cli.py"]
    core_dir = repo_root / "core"
    targets.extend(sorted(core_dir.rglob("*.py")))
    return [p for p in targets if p.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect except-pass in cli.py and core/*.py")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when violations are found")
    parser.add_argument("--root", default=".", help="Repo root path")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    hits = scan_paths(collect_default_targets(repo_root))
    if hits:
        print("except-pass findings:")
        for h in hits:
            print(f" - {h}")
        return 1 if args.strict else 0

    print("No except-pass findings in cli.py/core")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
