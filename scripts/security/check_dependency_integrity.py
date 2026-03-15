#!/usr/bin/env python3
"""Minimal supply-chain integrity checks for locked dependencies."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

# Keep this list to packages that are guaranteed in the current lock.
# Provider-specific SDKs can be optional per deployment.
CRITICAL_PACKAGES = {
    "openai",
    "httpx",
    "requests",
    "pydantic",
    "python-dotenv",
    "pyyaml",
}

# Editable entries for the project package itself are allowed.
ALLOWED_EDITABLE = {"openmork"}


def _load_lock(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def check_lock_integrity(lock_path: Path) -> tuple[bool, list[str]]:
    if not lock_path.exists():
        return False, [f"Missing lock file: {lock_path}"]

    data = _load_lock(lock_path)
    packages = data.get("package", [])
    by_name = {pkg.get("name"): pkg for pkg in packages if isinstance(pkg, dict) and pkg.get("name")}

    issues: list[str] = []
    for name in sorted(CRITICAL_PACKAGES):
        pkg = by_name.get(name)
        if not pkg:
            issues.append(f"Critical package not locked: {name}")
            continue
        version = str(pkg.get("version", "")).strip()
        if not version:
            issues.append(f"Critical package missing pinned version: {name}")

    for name, pkg in by_name.items():
        source = pkg.get("source")
        if isinstance(source, dict) and source.get("editable") and name not in ALLOWED_EDITABLE:
            issues.append(f"Editable dependency detected in lockfile: {name}")

    return len(issues) == 0, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check integrity of critical locked dependencies")
    parser.add_argument("--lock", default="uv.lock", help="Path to lock file (default: uv.lock)")
    args = parser.parse_args()

    ok, issues = check_lock_integrity(Path(args.lock))
    if ok:
        print("Dependency integrity check passed")
        return 0

    print("Dependency integrity check failed:", file=sys.stderr)
    for issue in issues:
        print(f"- {issue}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
