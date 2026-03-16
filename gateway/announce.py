"""Unified announce routing with domain/category overrides.

MVP:
- One announce router for gateway/ops events.
- Configurable per domain/category via YAML/JSON.
- Falls back to platform home channel when no route matches.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from openmork_cli.config import get_openmork_home


class AnnounceRouter:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (get_openmork_home() / "announce_routing.yaml")
        self._cfg = self._load()

    def _load(self) -> Dict[str, Any]:
        path = self.config_path
        if not path.exists():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                data = json.loads(text)
            else:
                data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def resolve_target(self, *, domain: Optional[str] = None, category: Optional[str] = None, default_target: Optional[str] = None) -> Optional[str]:
        routes = self._cfg.get("routes") if isinstance(self._cfg, dict) else None
        if not isinstance(routes, dict):
            return default_target

        by_domain = routes.get("domain")
        if domain and isinstance(by_domain, dict):
            hit = by_domain.get(domain)
            if isinstance(hit, str) and hit.strip():
                return hit.strip()

        by_category = routes.get("category")
        if category and isinstance(by_category, dict):
            hit = by_category.get(category)
            if isinstance(hit, str) and hit.strip():
                return hit.strip()

        fallback = routes.get("default")
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()

        return default_target
