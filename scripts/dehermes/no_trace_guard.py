#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
LEGACY_BRAND = "her" + "mes"
LEGACY_AGENT = LEGACY_BRAND + "-agent"
LEGACY_HOME = "HER" + "MES_HOME"
LEGACY_DOTDIR = "." + LEGACY_BRAND

# Zero-tolerance mode: no legacy references are allowed in tracked sources.
ALLOWED_FILES: set[str] = set()


def check_no_legacy_trace() -> bool:
    escaped_brand = re.escape(LEGACY_BRAND)
    escaped_agent = re.escape(LEGACY_AGENT)
    escaped_home = re.escape(LEGACY_HOME)
    escaped_dotdir = re.escape(LEGACY_DOTDIR)

    legacy_pattern = re.compile(
        rf"\\b(?:{escaped_brand}|{escaped_agent}|{escaped_home})\\b|{escaped_dotdir}|[/\\\\]{escaped_brand}(?:[/\\\\]|\\b)",
        re.IGNORECASE,
    )
    has_error = False

    for file_path in ROOT.rglob("*"):
        if not file_path.is_file():
            continue

        rel_path = str(file_path.relative_to(ROOT)).replace("\\", "/")

        if any(sk in rel_path for sk in [".git", "node_modules", "venv", ".venv", "__pycache__"]):
            continue

        if rel_path in ALLOWED_FILES:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        matches = legacy_pattern.findall(content)
        if matches:
            print(f"❌ [NO-TRACE GUARD] Legacy reference found in {rel_path}: {matches}")
            has_error = True

    return not has_error


if __name__ == "__main__":
    if check_no_legacy_trace():
        print("✅ [NO-TRACE GUARD] Passed. No legacy references found.")
        sys.exit(0)

    print("❌ [NO-TRACE GUARD] Failed. Remove all legacy references.")
    sys.exit(1)
