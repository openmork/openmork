#!/usr/bin/env python3
"""Lightweight reporting guard to avoid silent long-running work.

Usage:
  reporting_guard.py start <task_id> [--ttl-min 12]
  reporting_guard.py progress <task_id> [--note "..."]
  reporting_guard.py done <task_id>
  reporting_guard.py check [--ttl-min 12] [--cooldown-min 30]

The check command is designed for periodic execution (cron/systemd timer).
It emits a single-line alert only when a task is overdue and cooldown passed.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path

STATE = Path.home() / ".openmork" / "ops" / "reporting_guard_state.json"


def _load():
    if not STATE.exists():
        return {"tasks": {}, "last_alerts": {}}
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"tasks": {}, "last_alerts": {}}


def _save(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2))


def start(task_id: str, ttl_min: int):
    d = _load()
    now = int(time.time())
    d.setdefault("tasks", {})[task_id] = {
        "status": "running",
        "started_at": now,
        "last_progress_at": now,
        "ttl_min": ttl_min,
    }
    _save(d)
    print(f"GUARD_OK started:{task_id}")


def progress(task_id: str, note: str | None):
    d = _load(); now = int(time.time())
    t = d.setdefault("tasks", {}).get(task_id)
    if not t:
        print(f"GUARD_WARN task_not_found:{task_id}")
        return
    t["last_progress_at"] = now
    if note:
        t["last_note"] = note[:300]
    _save(d)
    print(f"GUARD_OK progress:{task_id}")


def done(task_id: str):
    d = _load(); now = int(time.time())
    t = d.setdefault("tasks", {}).get(task_id)
    if not t:
        print(f"GUARD_WARN task_not_found:{task_id}")
        return
    t["status"] = "done"
    t["done_at"] = now
    _save(d)
    print(f"GUARD_OK done:{task_id}")


def check(default_ttl_min: int, cooldown_min: int):
    d = _load(); now = int(time.time())
    tasks = d.setdefault("tasks", {})
    alerts = d.setdefault("last_alerts", {})
    overdue = []
    for tid, t in tasks.items():
        if t.get("status") != "running":
            continue
        ttl = int(t.get("ttl_min") or default_ttl_min)
        last = int(t.get("last_progress_at") or t.get("started_at") or now)
        if now - last >= ttl * 60:
            last_alert = int(alerts.get(tid, 0))
            if now - last_alert >= cooldown_min * 60:
                overdue.append((tid, (now - last) // 60))
                alerts[tid] = now
    _save(d)
    if not overdue:
        print("GUARD_OK no_overdue_tasks")
        return
    # single compact line to avoid token noise
    payload = ", ".join([f"{tid}:{mins}m" for tid, mins in overdue])
    print(f"GUARD_ALERT overdue_tasks {payload}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start"); s.add_argument("task_id"); s.add_argument("--ttl-min", type=int, default=12)
    p = sub.add_parser("progress"); p.add_argument("task_id"); p.add_argument("--note", default=None)
    d = sub.add_parser("done"); d.add_argument("task_id")
    c = sub.add_parser("check"); c.add_argument("--ttl-min", type=int, default=12); c.add_argument("--cooldown-min", type=int, default=30)

    a = ap.parse_args()
    if a.cmd == "start": start(a.task_id, a.ttl_min)
    elif a.cmd == "progress": progress(a.task_id, a.note)
    elif a.cmd == "done": done(a.task_id)
    elif a.cmd == "check": check(a.ttl_min, a.cooldown_min)


if __name__ == "__main__":
    main()
