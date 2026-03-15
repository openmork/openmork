#!/usr/bin/env python3
"""Compute a De-Hermes independence score (0-100) with transparent components."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "dehermes_score.json"

EXCLUDE_DIRS = {".git", ".venv", "node_modules", ".pytest_cache", "__pycache__"}
EXCLUDE_PATH_PREFIXES = ("reports/",)
EXCLUDE_PATHS = {
    "scripts/dehermes/score.py",
    "docs/architecture/DEHERMES_AUDIT.md",
    "docs/architecture/DEHERMES_ROADMAP.md",
}
TEXT_EXTS = {
    ".py", ".md", ".toml", ".lock", ".json", ".yaml", ".yml", ".ps1", ".cmd", ".sh", ".svg", ".txt",
}

PATTERNS = {
    "hermes_agent_name": re.compile(r"hermes-agent", re.IGNORECASE),
    "hermes_cli": re.compile(r"hermes_cli", re.IGNORECASE),
    "hermes_home_env": re.compile(r"\bHERMES_HOME\b"),
    "legacy_path_dot_hermes": re.compile(r"\.hermes|[/\\]hermes([/\\]|\b)", re.IGNORECASE),
    "brand_hermes": re.compile(r"\bHermes\b|\bHERMES\b|\bhermes\b"),
}

CATEGORY_WEIGHT = {"code": 3, "config": 2, "docs": 1}
DEPENDENCY_HIT_WEIGHT = 6
PATH_HIT_WEIGHT = 4
PENALTY_SCALE = 40


def iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in EXCLUDE_PATHS or any(rel.startswith(prefix) for prefix in EXCLUDE_PATH_PREFIXES):
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        yield p


def classify(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith(("docs/", "website/")) or path.suffix.lower() == ".md":
        return "docs"
    if path.suffix.lower() in {".toml", ".lock", ".json", ".yaml", ".yml"}:
        return "config"
    return "code"


def compute_score(penalty: int) -> int:
    # Smooth decay to avoid permanent clamp at 0 while keeping monotonic behavior.
    score = round(100 / (1 + (penalty / PENALTY_SCALE)))
    return max(0, min(100, score))


def main() -> int:
    per_file = defaultdict(lambda: Counter())
    category_totals = Counter()

    for f in iter_files(ROOT):
        rel = f.relative_to(ROOT).as_posix()
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        cat = classify(f)
        for key, pattern in PATTERNS.items():
            count = len(pattern.findall(text))
            if count:
                per_file[rel][key] += count
                category_totals[cat] += count

    dep_files = [ROOT / "pyproject.toml", ROOT / "uv.lock", ROOT / "package-lock.json"]
    dependency_legacy_hits = 0
    for dp in dep_files:
        if dp.exists():
            dependency_legacy_hits += len(PATTERNS["hermes_agent_name"].findall(dp.read_text(encoding="utf-8")))

    path_legacy_hits = 0
    for stats in per_file.values():
        path_legacy_hits += stats.get("legacy_path_dot_hermes", 0) + stats.get("hermes_home_env", 0)

    weighted_refs = sum(category_totals[c] * CATEGORY_WEIGHT[c] for c in category_totals)
    dependency_penalty = dependency_legacy_hits * DEPENDENCY_HIT_WEIGHT
    path_penalty = path_legacy_hits * PATH_HIT_WEIGHT
    penalty = weighted_refs + dependency_penalty + path_penalty
    score = compute_score(penalty)

    top_files = []
    for rel, stats in per_file.items():
        total = sum(stats.values())
        top_files.append({"file": rel, "total_refs": total, "breakdown": dict(stats)})
    top_files.sort(key=lambda x: x["total_refs"], reverse=True)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "formula": "score = round(100 / (1 + penalty/40)); penalty = weighted_refs + dependency_legacy_hits*6 + path_legacy_hits*4",
        "weights": {
            "category_weight": CATEGORY_WEIGHT,
            "dependency_hit_weight": DEPENDENCY_HIT_WEIGHT,
            "path_hit_weight": PATH_HIT_WEIGHT,
            "penalty_scale": PENALTY_SCALE,
        },
        "totals": {
            "refs_by_category": dict(category_totals),
            "dependency_legacy_hits": dependency_legacy_hits,
            "path_legacy_hits": path_legacy_hits,
            "weighted_refs": weighted_refs,
            "dependency_penalty": dependency_penalty,
            "path_penalty": path_penalty,
            "penalty": penalty,
        },
        "top_files": top_files[:20],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"refs_by_category={dict(category_totals)}")
    print(
        "penalty_components="
        f"weighted_refs:{weighted_refs},dependency_penalty:{dependency_penalty},path_penalty:{path_penalty},total:{penalty}"
    )
    print(f"score={score}")
    print(f"report={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
