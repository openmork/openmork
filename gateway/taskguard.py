"""Event-driven reporting guard integration for gateway long tasks.

Keeps the same state file semantics as scripts/ops/reporting_guard.py while adding
manual override flags for gateway command control.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


class ReportingTaskGuard:
    def __init__(
        self,
        state_path: Path | None = None,
        default_ttl_min: int = 12,
        default_cooldown_min: int = 30,
    ) -> None:
        self.state_path = state_path or (Path.home() / ".openmork" / "ops" / "reporting_guard_state.json")
        self.default_ttl_min = default_ttl_min
        self.default_cooldown_min = default_cooldown_min

    def _load(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"tasks": {}, "last_alerts": {}, "manual_overrides": {}}
        try:
            data = json.loads(self.state_path.read_text())
            data.setdefault("tasks", {})
            data.setdefault("last_alerts", {})
            data.setdefault("manual_overrides", {})
            return data
        except Exception:
            return {"tasks": {}, "last_alerts": {}, "manual_overrides": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, indent=2))

    def start(self, task_id: str, ttl_min: int | None = None) -> None:
        d = self._load()
        now = int(time.time())
        d["tasks"][task_id] = {
            "status": "running",
            "started_at": now,
            "last_progress_at": now,
            "ttl_min": int(ttl_min or self.default_ttl_min),
        }
        self._save(d)

    def progress(self, task_id: str, note: str | None = None) -> None:
        d = self._load()
        t = d["tasks"].get(task_id)
        if not t:
            return
        t["last_progress_at"] = int(time.time())
        if note:
            t["last_note"] = note[:300]
        self._save(d)

    def done(self, task_id: str) -> None:
        d = self._load()
        t = d["tasks"].get(task_id)
        if not t:
            return
        t["status"] = "done"
        t["done_at"] = int(time.time())
        self._save(d)

    def set_manual(self, task_id: str, enabled: bool) -> None:
        d = self._load()
        d["manual_overrides"][task_id] = bool(enabled)
        self._save(d)

    def is_manual_enabled(self, task_id: str) -> bool:
        d = self._load()
        return bool(d.get("manual_overrides", {}).get(task_id, False))

    def status(self, task_id: str) -> Dict[str, Any]:
        d = self._load()
        task = d.get("tasks", {}).get(task_id)
        return {
            "task_id": task_id,
            "manual_enabled": bool(d.get("manual_overrides", {}).get(task_id, False)),
            "task": task,
            "last_alert_at": int(d.get("last_alerts", {}).get(task_id, 0)),
        }

    def check(self, ttl_min: int | None = None, cooldown_min: int | None = None) -> list[dict[str, Any]]:
        d = self._load()
        now = int(time.time())
        ttl_default = int(ttl_min or self.default_ttl_min)
        cooldown = int(cooldown_min or self.default_cooldown_min)

        overdue: list[dict[str, Any]] = []
        for tid, task in d.get("tasks", {}).items():
            if task.get("status") != "running":
                continue
            ttl = int(task.get("ttl_min") or ttl_default)
            last = int(task.get("last_progress_at") or task.get("started_at") or now)
            if now - last < ttl * 60:
                continue
            last_alert = int(d.get("last_alerts", {}).get(tid, 0))
            if now - last_alert < cooldown * 60:
                continue
            mins = (now - last) // 60
            overdue.append({"task_id": tid, "minutes_silent": int(mins)})
            d.setdefault("last_alerts", {})[tid] = now

        self._save(d)
        return overdue
