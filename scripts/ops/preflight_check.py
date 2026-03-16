#!/usr/bin/env python3
"""Openmork P0 preflight check (blocking).

Validates:
- provider/model is operational (minimal smoke prompt)
- basic web fetch connectivity
- safety config loaded (safety.yaml + tirith flags)
- pairing/home channel configured

Writes JSON summary to reports/preflight_status.json and exits non-zero on critical failures.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openmork_cli.config import get_openmork_home, get_env_value, load_config

REPORT_PATH = ROOT / "reports" / "preflight_status.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_provider_model() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "provider_model", "ok": False, "critical": True}
    cfg = load_config()
    model_cfg = cfg.get("model")
    if isinstance(model_cfg, dict):
        model = (model_cfg.get("default") or model_cfg.get("name") or "").strip()
        requested_provider = (model_cfg.get("provider") or "auto").strip().lower()
        cfg_base_url = (model_cfg.get("base_url") or "").strip()
    else:
        model = str(model_cfg or "").strip()
        requested_provider = "auto"
        cfg_base_url = ""

    if not model:
        result["error"] = "No model configured"
        return result

    provider = requested_provider if requested_provider and requested_provider != "auto" else "openrouter"
    api_mode = "chat_completions"

    if provider in {"anthropic", "claude"}:
        api_mode = "anthropic_messages"
        base_url = "https://api.anthropic.com"
        api_key = (get_env_value("ANTHROPIC_TOKEN") or get_env_value("ANTHROPIC_API_KEY") or "").strip()
    elif provider in {"openai-codex", "codex", "openai"}:
        api_mode = "codex_responses"
        base_url = (get_env_value("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip()
        api_key = (get_env_value("OPENAI_API_KEY") or "").strip()
    else:
        base_url = (get_env_value("OPENAI_BASE_URL") or cfg_base_url or get_env_value("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").strip()
        api_key = (get_env_value("OPENROUTER_API_KEY") or get_env_value("OPENAI_API_KEY") or "").strip()

    base_url = base_url.rstrip("/")
    result.update({"provider": provider, "api_mode": api_mode, "model": model, "base_url": base_url})

    if not base_url or not api_key:
        result["error"] = "Missing runtime base_url or api_key"
        return result

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = None
    url = None

    if api_mode == "anthropic_messages":
        url = f"{base_url}/v1/messages"
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        headers.pop("Authorization", None)
        payload = {
            "model": model,
            "max_tokens": 8,
            "messages": [{"role": "user", "content": "ping"}],
        }
    elif api_mode == "codex_responses":
        url = f"{base_url}/responses"
        payload = {"model": model, "input": "ping", "max_output_tokens": 8}
    else:
        url = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "max_tokens": 8,
            "temperature": 0,
            "messages": [{"role": "user", "content": "ping"}],
        }

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            code = int(getattr(resp, "status", 200))
            txt = resp.read(800).decode("utf-8", errors="ignore")
        result["status_code"] = code
        if 200 <= code < 300:
            result["ok"] = True
            return result
        result["error"] = f"Smoke prompt failed ({code})"
        if txt.strip():
            result["response_snippet"] = txt.strip()[:400]
    except Exception as e:
        result["error"] = f"Smoke prompt exception: {e}"

    return result


def check_web_fetch() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "web_fetch", "ok": False, "critical": True}
    url = os.getenv("OPENMORK_PREFLIGHT_WEB_URL", "https://example.com")
    result["url"] = url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "openmork-preflight/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read(256).decode("utf-8", errors="ignore")
        result["status_code"] = int(status)
        result["ok"] = 200 <= int(status) < 400 and len(body.strip()) > 0
        if not result["ok"]:
            result["error"] = "Web fetch returned empty/invalid response"
    except Exception as e:
        result["error"] = f"Web fetch failed: {e}"
    return result


def check_safety() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "safety", "ok": False, "critical": True}
    home = get_openmork_home()
    safety_file = home / "safety.yaml"
    fallback_file = ROOT / "safety.yaml.default"

    security_cfg = (load_config().get("security") or {}) if isinstance(load_config().get("security"), dict) else {}
    env_tirith_enabled = os.getenv("TIRITH_ENABLED")
    if env_tirith_enabled is None:
        tirith_enabled = bool(security_cfg.get("tirith_enabled", True))
    else:
        tirith_enabled = env_tirith_enabled.strip().lower() in {"1", "true", "yes", "on"}
    tirith_path = (os.getenv("TIRITH_BIN") or str(security_cfg.get("tirith_path") or "tirith")).strip()

    safety_present = safety_file.exists() or fallback_file.exists()
    result.update(
        {
            "safety_yaml": str(safety_file if safety_file.exists() else fallback_file),
            "safety_yaml_exists": safety_present,
            "tirith_enabled": tirith_enabled,
            "tirith_path": tirith_path,
        }
    )

    if safety_present and tirith_enabled and tirith_path:
        result["ok"] = True
    else:
        missing = []
        if not safety_present:
            missing.append("safety.yaml")
        if not tirith_enabled:
            missing.append("tirith_enabled")
        if not tirith_path:
            missing.append("tirith_path")
        result["error"] = "Missing/invalid safety config: " + ", ".join(missing)
    return result


def _configured_platforms() -> list[tuple[str, str, str | None, str | None]]:
    return [
        ("telegram", "TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL", "TELEGRAM_ALLOWED_USERS"),
        ("discord", "DISCORD_BOT_TOKEN", "DISCORD_HOME_CHANNEL", "DISCORD_ALLOWED_USERS"),
        ("slack", "SLACK_BOT_TOKEN", "SLACK_HOME_CHANNEL", "SLACK_ALLOWED_USERS"),
        ("signal", "SIGNAL_HTTP_URL", "SIGNAL_HOME_CHANNEL", "SIGNAL_ALLOWED_USERS"),
        ("email", "EMAIL_ADDRESS", "EMAIL_HOME_ADDRESS", "EMAIL_ALLOWED_USERS"),
    ]


def check_pairing_home_channel() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "pairing_home_channel", "ok": False, "critical": True}
    configured: list[dict[str, Any]] = []

    pairing_dir = get_openmork_home() / "pairing"
    has_any_pairing_approved = False
    if pairing_dir.exists():
        for approved_file in pairing_dir.glob("*-approved.json"):
            try:
                payload = json.loads(approved_file.read_text(encoding="utf-8") or "{}")
                if isinstance(payload, dict) and payload:
                    has_any_pairing_approved = True
                    break
            except Exception:
                continue

    for platform, token_key, home_key, allow_key in _configured_platforms():
        token = (get_env_value(token_key) or "").strip()
        if not token:
            continue
        home = (get_env_value(home_key) or "").strip() if home_key else ""
        allow = (get_env_value(allow_key) or "").strip() if allow_key else ""
        configured.append(
            {
                "platform": platform,
                "home_channel_set": bool(home),
                "allowlist_set": bool(allow),
            }
        )

    if not configured:
        result["error"] = "No messaging platform configured"
        result["platforms"] = []
        return result

    missing = [p["platform"] for p in configured if not p["home_channel_set"]]
    auth_ok = all(p["allowlist_set"] for p in configured) or has_any_pairing_approved

    result["platforms"] = configured
    result["pairing_approved_present"] = has_any_pairing_approved

    if not missing and auth_ok:
        result["ok"] = True
    else:
        chunks = []
        if missing:
            chunks.append(f"home channel missing for: {', '.join(missing)}")
        if not auth_ok:
            chunks.append("no allowlist and no approved pairing users")
        result["error"] = "; ".join(chunks)

    return result


def main() -> int:
    checks = [
        check_provider_model(),
        check_web_fetch(),
        check_safety(),
        check_pairing_home_channel(),
    ]

    critical_failed = [c for c in checks if c.get("critical") and not c.get("ok")]
    status = "pass" if not critical_failed else "fail"

    payload = {
        "timestamp": now_iso(),
        "status": status,
        "critical_failed": [c.get("name") for c in critical_failed],
        "checks": checks,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Preflight: {status.upper()} ({REPORT_PATH})")
    for c in checks:
        mark = "OK" if c.get("ok") else "FAIL"
        print(f"- [{mark}] {c.get('name')}")
        if not c.get("ok") and c.get("error"):
            print(f"    {c['error']}")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
