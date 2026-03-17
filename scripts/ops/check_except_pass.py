#!/usr/bin/env python3
"""Detect silent ``except ...: pass`` blocks in production Python code.

Default scope is repository-wide but excludes non-production zones:
- tests/
- docs/
- optional-skills/
- reports/
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

EXCEPT_PASS_RE = re.compile(r"except(?:\s+(?:Exception|BaseException))?\s*:\s*\n\s*pass\b", re.MULTILINE)
DEFAULT_EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "node_modules", "tests", "docs", "optional-skills", "reports"}


def scan_paths(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in EXCEPT_PASS_RE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"{p}:{line}")
    return hits


def collect_python_targets(repo_root: Path, exclude_dirs: set[str] | None = None) -> list[Path]:
    exclude_dirs = exclude_dirs or DEFAULT_EXCLUDE_DIRS
    targets: list[Path] = []
    for p in repo_root.rglob("*.py"):
        if any(part in exclude_dirs for part in p.parts):
            continue
        targets.append(p)
    return sorted(targets)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect except-pass in repository Python files")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when findings exceed allowed threshold")
    parser.add_argument("--max-findings", type=int, default=0, help="Allowed finding count when --strict is used")
    parser.add_argument("--root", default=".", help="Repo root path")
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Additional directory name to exclude (repeatable)",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_dirs.update(args.exclude_dir)

    hits = scan_paths(collect_python_targets(repo_root, exclude_dirs=exclude_dirs))
    if hits:
        print("except-pass findings:")
        for h in hits:
            print(f" - {h}")
        print(f"Total findings: {len(hits)}")
        if args.strict and len(hits) > max(args.max_findings, 0):
            return 1
        return 0

    print("No except-pass findings in production Python scope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
