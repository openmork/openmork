#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()
LEGACY_BRAND = "her" + "mes"

# Minimal allowlist: only historical/audit files that intentionally retain legacy text.
# Each exception below is temporary and tracked in docs/architecture/DEHERMES_NOTRACE_AUDIT.md.
ALLOWED_FILES = {
    # Scoring and audit artifacts for this migration stream.
    "scripts/dehermes/score.py",
    "reports/dehermes_score.json",
    "docs/architecture/DEHERMES_AUDIT.md",
    "docs/architecture/DEHERMES_ROADMAP.md",
    "docs/architecture/DEHERMES_NOTRACE_AUDIT.md",
    "ops/openmork/GEMINI_NOTRACE_SPRINT.md",
    # Historical example data (mythology context, not product branding).
    "datagen-config-examples/example_browser_tasks.jsonl",
}


def check_no_legacy_trace() -> bool:
    legacy_pattern = re.compile(rf"\b{LEGACY_BRAND}(?:-agent)?\b", re.IGNORECASE)
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
        print("✅ [NO-TRACE GUARD] Passed. No unauthorized legacy references found.")
        sys.exit(0)

    print("❌ [NO-TRACE GUARD] Failed. Clean up legacy references or add to allowlist if strictly historical.")
    sys.exit(1)
