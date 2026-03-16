#!/usr/bin/env python3
"""Refactor T1 preflight check (blocking).

Checks mínimos:
- auth runtime (provider/model + credenciales)
- deps básicas (python modules + binarios)
- seguridad (safety.yaml + tirith flags)
- conectividad web básica
- sanity de repo (archivos/directorios core)

Salida JSON: reports/refactor_preflight_status.json
Exit code: != 0 si falla check crítico.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openmork_cli.config import get_openmork_home, get_env_value, load_config

REPORT_PATH = ROOT / "reports" / "refactor_preflight_status.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_auth_runtime() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "auth_runtime", "ok": False, "critical": True}
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
    if provider in {"anthropic", "claude"}:
        base_url = "https://api.anthropic.com"
        api_key = (get_env_value("ANTHROPIC_TOKEN") or get_env_value("ANTHROPIC_API_KEY") or "").strip()
    elif provider in {"openai-codex", "codex", "openai"}:
        base_url = (get_env_value("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip()
        api_key = (get_env_value("OPENAI_API_KEY") or "").strip()
    else:
        base_url = (
            get_env_value("OPENAI_BASE_URL")
            or cfg_base_url
            or get_env_value("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        ).strip()
        api_key = (get_env_value("OPENROUTER_API_KEY") or get_env_value("OPENAI_API_KEY") or "").strip()

    result.update(
        {
            "provider": provider,
            "model": model,
            "base_url": base_url.rstrip("/"),
            "api_key_present": bool(api_key),
        }
    )

    if not base_url or not api_key:
        result["error"] = "Missing runtime base_url or api_key"
        return result

    result["ok"] = True
    return result


def check_basic_deps() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "basic_deps", "ok": False, "critical": True}
    modules = ["yaml", "requests"]
    bins = ["git", "python3"]

    missing_modules = [m for m in modules if importlib.util.find_spec(m) is None]
    missing_bins = [b for b in bins if shutil.which(b) is None]

    result.update(
        {
            "python": sys.version.split()[0],
            "required_modules": modules,
            "missing_modules": missing_modules,
            "required_bins": bins,
            "missing_bins": missing_bins,
        }
    )

    if missing_modules or missing_bins:
        chunks = []
        if missing_modules:
            chunks.append(f"missing modules: {', '.join(missing_modules)}")
        if missing_bins:
            chunks.append(f"missing bins: {', '.join(missing_bins)}")
        result["error"] = "; ".join(chunks)
        return result

    result["ok"] = True
    return result


def check_safety_flags() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "safety_flags", "ok": False, "critical": True}

    home = get_openmork_home()
    safety_file = home / "safety.yaml"
    fallback_file = ROOT / "safety.yaml.default"

    cfg = load_config()
    security_cfg = cfg.get("security") if isinstance(cfg.get("security"), dict) else {}

    env_tirith_enabled = os.getenv("TIRITH_ENABLED")
    if env_tirith_enabled is None:
        tirith_enabled = bool((security_cfg or {}).get("tirith_enabled", True))
    else:
        tirith_enabled = env_tirith_enabled.strip().lower() in {"1", "true", "yes", "on"}

    tirith_path = (os.getenv("TIRITH_BIN") or str((security_cfg or {}).get("tirith_path") or "tirith")).strip()
    safety_present = safety_file.exists() or fallback_file.exists()

    result.update(
        {
            "safety_yaml": str(safety_file if safety_file.exists() else fallback_file),
            "safety_yaml_exists": safety_present,
            "tirith_enabled": tirith_enabled,
            "tirith_path": tirith_path,
        }
    )

    if not safety_present or not tirith_enabled or not tirith_path:
        missing = []
        if not safety_present:
            missing.append("safety.yaml")
        if not tirith_enabled:
            missing.append("tirith_enabled")
        if not tirith_path:
            missing.append("tirith_path")
        result["error"] = "Missing/invalid safety config: " + ", ".join(missing)
        return result

    result["ok"] = True
    return result


def check_web_connectivity() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "web_connectivity", "ok": False, "critical": True}
    url = os.getenv("OPENMORK_PREFLIGHT_WEB_URL", "https://example.com")
    result["url"] = url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "openmork-refactor-preflight/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = int(getattr(resp, "status", 200))
            snippet = resp.read(200).decode("utf-8", errors="ignore")
        result["status_code"] = status
        result["ok"] = 200 <= status < 400 and len(snippet.strip()) > 0
        if not result["ok"]:
            result["error"] = "Empty/invalid HTTP response"
    except Exception as e:
        result["error"] = f"Web connectivity failed: {e}"
    return result


def check_repo_sanity() -> dict[str, Any]:
    result: dict[str, Any] = {"name": "repo_sanity", "ok": False, "critical": True}

    required_paths = [
        ROOT / ".git",
        ROOT / "run_agent.py",
        ROOT / "cli.py",
        ROOT / "openmork_cli",
        ROOT / "tests",
    ]

    missing = [str(p.relative_to(ROOT)) for p in required_paths if not p.exists()]
    result["required_paths"] = [str(p.relative_to(ROOT)) for p in required_paths]
    result["missing_paths"] = missing

    if missing:
        result["error"] = "Missing required repo paths: " + ", ".join(missing)
        return result

    result["ok"] = True
    return result


def main() -> int:
    checks = [
        check_auth_runtime(),
        check_basic_deps(),
        check_safety_flags(),
        check_web_connectivity(),
        check_repo_sanity(),
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

    print(f"Refactor preflight: {status.upper()} ({REPORT_PATH})")
    for c in checks:
        mark = "OK" if c.get("ok") else "FAIL"
        print(f"- [{mark}] {c.get('name')}")
        if not c.get("ok") and c.get("error"):
            print(f"    {c['error']}")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
