#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.resolve()

ALLOWED_FILES = {
    # Historicos y herramientas de la migración
    "scripts/dehermes/score.py",
    "scripts/dehermes/no_trace_guard.py",
    "reports/dehermes_score.json",
    "docs/architecture/DEHERMES_AUDIT.md",
    "docs/architecture/DEHERMES_ROADMAP.md",
    "docs/architecture/DEHERMES_NOTRACE_AUDIT.md",
    "ops/openmork/GEMINI_NOTRACE_SPRINT.md",
    # Shims de compatibilidad temporales (documentados en roadmap)
    "scripts/install.ps1",
    "scripts/install.cmd",
    "scripts/hermes.ps1",
    "scripts/hermes.cmd",
    # Datagen mitológico
    "datagen-config-examples/example_browser_tasks.jsonl",
}

def check_no_hermes_trace() -> bool:
    hermes_pattern = re.compile(r'\bhermes(?:-agent)?\b', re.IGNORECASE)
    has_error = False

    for file_path in ROOT.rglob("*"):
        if not file_path.is_file():
            continue
            
        rel_path = str(file_path.relative_to(ROOT))
        
        # Ignorar directorios de git, node_modules y entornos virtuales
        if any(sk in rel_path for sk in [".git", "node_modules", "venv", ".venv", "__pycache__"]):
            continue
            
        if rel_path.replace("\\", "/") in ALLOWED_FILES:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        matches = hermes_pattern.findall(content)
        if matches:
            print(f"❌ [NO-TRACE GUARD] Legacy reference found in {rel_path}: {matches}")
            has_error = True

    return not has_error

if __name__ == "__main__":
    if check_no_hermes_trace():
        print("✅ [NO-TRACE GUARD] Passed. No unauthorized legacy references found.")
        sys.exit(0)
    else:
        print("❌ [NO-TRACE GUARD] Failed. Clean up 'hermes' references or add to allowlist if strictly historical.")
        sys.exit(1)
