#!/usr/bin/env python3
"""Operational secret scanner for repository content and git remotes.

Checks:
1) staged files (default) or whole repo (`--all-files`) for common secret patterns
2) git remotes for embedded credentials (e.g. https://token@github.com/...)

Exit code 1 when findings are detected.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SECRET_PATTERNS = [
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]

REMOTE_TOKEN_RE = re.compile(r"https://[^\s/@:]+@")
IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
IGNORE_FILE_SUFFIXES = (".example",)
IGNORE_PATH_PARTS = {"tests", "docs", "skills"}
IGNORE_FILE_NAMES = {".env.example"}


def _run(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    return (res.stdout or "")


def _git_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def _staged_files(root: Path) -> list[Path]:
    out = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], root)
    files = [root / line.strip() for line in out.splitlines() if line.strip()]
    return [p for p in files if _should_scan(p)]


def _should_scan(path: Path) -> bool:
    if any(part in IGNORE_DIRS for part in path.parts):
        return False
    if any(part in IGNORE_PATH_PARTS for part in path.parts):
        return False
    if path.name in IGNORE_FILE_NAMES:
        return False
    if path.suffix in IGNORE_FILE_SUFFIXES:
        return False
    return True


def _repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if not _should_scan(p):
            continue
        files.append(p)
    return files


def _scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []

    findings: list[str] = []
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"{path}: matched {name}")
    return findings


def _scan_remotes(root: Path) -> list[str]:
    out = _run(["git", "remote", "-v"], root)
    findings: list[str] = []
    for line in out.splitlines():
        if REMOTE_TOKEN_RE.search(line):
            findings.append(f"remote contains embedded credential: {line}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan for leaked secrets and unsafe git remotes")
    parser.add_argument("--all-files", action="store_true", help="Scan full repo instead of staged files")
    args = parser.parse_args()

    root = _git_root()
    files = _repo_files(root) if args.all_files else _staged_files(root)

    findings: list[str] = []
    for f in files:
        findings.extend(_scan_file(f))

    findings.extend(_scan_remotes(root))

    if findings:
        print("❌ Security check failed. Potential secrets or unsafe remotes detected:")
        for item in findings:
            print(f"  - {item}")
        print("\nFix findings before commit/push.")
        return 1

    print("✅ Security check passed: no obvious secrets or embedded remote credentials found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
