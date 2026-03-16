"""Internal LLM gateway for provider/key routing in DEV.

MVP goals:
- Load provider/key pool from an external YAML config (path via env).
- Weighted round-robin selection with health-aware filtering.
- Sticky routing per conversation.
- Key/provider state transitions for 401/403 (quarantine) and 429 (cooldown).

This module does NOT attempt to bypass provider terms. It only supports
legitimate multi-provider/multi-key failover and balancing.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from openmork_cli.config import load_config


DEFAULT_CONFIG_ENV = "OPENMORK_LLM_GATEWAY_CONFIG"
DEFAULT_ENABLED_ENV = "OPENMORK_LLM_GATEWAY_ENABLED"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


@dataclass
class GatewayRoute:
    route_id: str
    provider: str
    base_url: str
    api_key_env: str = ""
    api_key: str = ""
    models: List[str] = field(default_factory=list)
    weight: int = 1
    cost_tier: int = 100
    latency_tier: int = 100
    api_mode: str = "chat_completions"


@dataclass
class GatewayState:
    quarantined_until: float = 0.0
    cooldown_until: float = 0.0
    last_error: str = ""

    def is_available(self, now: float) -> bool:
        return now >= self.quarantined_until and now >= self.cooldown_until


class LLMGateway:
    def __init__(self, config: Dict[str, Any], now_fn=time.time) -> None:
        self._config = config
        self._now = now_fn
        self._lock = threading.RLock()

        policy = config.get("policy") if isinstance(config.get("policy"), dict) else {}
        self.cooldown_seconds = int(policy.get("cooldown_seconds", 60))
        self.quarantine_seconds = int(policy.get("quarantine_seconds", 3600))

        self._routes: List[GatewayRoute] = []
        self._states: Dict[str, GatewayState] = {}
        self._sticky: Dict[str, str] = {}
        self._cursor_by_model: Dict[str, int] = {}

        self._build_routes(config)

    def _build_routes(self, config: Dict[str, Any]) -> None:
        providers = config.get("providers") if isinstance(config.get("providers"), list) else []
        for entry in providers:
            if not isinstance(entry, dict):
                continue
            route_id = str(entry.get("id", "")).strip()
            provider = str(entry.get("provider", "")).strip().lower()
            base_url = str(entry.get("base_url", "")).strip().rstrip("/")
            if not route_id or not provider or not base_url:
                continue

            api_key_env = str(entry.get("api_key_env", "")).strip()
            api_key = str(entry.get("api_key", "")).strip()
            models = entry.get("models") if isinstance(entry.get("models"), list) else ["*"]
            models = [str(m).strip() for m in models if str(m).strip()]
            if not models:
                models = ["*"]

            route = GatewayRoute(
                route_id=route_id,
                provider=provider,
                base_url=base_url,
                api_key_env=api_key_env,
                api_key=api_key,
                models=models,
                weight=max(1, int(entry.get("weight", 1))),
                cost_tier=int(entry.get("cost_tier", 100)),
                latency_tier=int(entry.get("latency_tier", 100)),
                api_mode=str(entry.get("api_mode", "chat_completions") or "chat_completions").strip(),
            )
            self._routes.append(route)
            self._states[route.route_id] = GatewayState()

    def _resolve_api_key(self, route: GatewayRoute) -> str:
        if route.api_key_env:
            return os.getenv(route.api_key_env, "").strip()
        return route.api_key

    def _matches_model(self, route: GatewayRoute, requested_model: str) -> bool:
        req = (requested_model or "").strip()
        if "*" in route.models:
            return True
        if not req:
            return True
        return req in route.models

    def _healthy_routes(self, requested_model: str, now: float) -> List[GatewayRoute]:
        healthy: List[GatewayRoute] = []
        for route in self._routes:
            if not self._matches_model(route, requested_model):
                continue
            state = self._states[route.route_id]
            if not state.is_available(now):
                continue
            if not self._resolve_api_key(route):
                continue
            healthy.append(route)
        healthy.sort(key=lambda r: (r.cost_tier, r.latency_tier, r.route_id))
        return healthy

    def _weighted_pool(self, routes: List[GatewayRoute]) -> List[GatewayRoute]:
        weighted: List[GatewayRoute] = []
        for route in routes:
            weighted.extend([route] * max(1, route.weight))
        return weighted

    def resolve_gateway_route(self, conversation_id: str, requested_model: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            now = float(self._now())
            conv_id = str(conversation_id or "").strip()
            model_key = str(requested_model or "*").strip() or "*"

            if conv_id and conv_id in self._sticky:
                sticky_id = self._sticky[conv_id]
                route = next((r for r in self._routes if r.route_id == sticky_id), None)
                if route and self._matches_model(route, requested_model):
                    state = self._states.get(route.route_id)
                    if state and state.is_available(now):
                        api_key = self._resolve_api_key(route)
                        if api_key:
                            return {
                                "route_id": route.route_id,
                                "provider": route.provider,
                                "api_mode": route.api_mode,
                                "base_url": route.base_url,
                                "api_key": api_key,
                                "requested_model": requested_model,
                                "sticky": True,
                            }

            healthy = self._healthy_routes(requested_model, now)
            if not healthy:
                return None

            weighted = self._weighted_pool(healthy)
            cursor = self._cursor_by_model.get(model_key, 0) % len(weighted)
            selected = weighted[cursor]
            self._cursor_by_model[model_key] = (cursor + 1) % len(weighted)

            if conv_id:
                self._sticky[conv_id] = selected.route_id

            return {
                "route_id": selected.route_id,
                "provider": selected.provider,
                "api_mode": selected.api_mode,
                "base_url": selected.base_url,
                "api_key": self._resolve_api_key(selected),
                "requested_model": requested_model,
                "sticky": bool(conv_id),
            }

    def report_route_result(self, route_id: str, status_code: Optional[int] = None) -> None:
        with self._lock:
            state = self._states.get(route_id)
            if not state:
                return

            now = float(self._now())
            if status_code in (401, 403):
                state.quarantined_until = now + self.quarantine_seconds
                state.last_error = f"http_{status_code}"
            elif status_code == 429:
                state.cooldown_until = now + self.cooldown_seconds
                state.last_error = "http_429"
            elif status_code is not None and 200 <= status_code < 400:
                # On successful requests, clear temporary throttling signals.
                state.cooldown_until = 0.0
                state.last_error = ""

    def get_route_state(self, route_id: str) -> Optional[GatewayState]:
        return self._states.get(route_id)


def _read_gateway_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


def _gateway_enabled_from_config() -> bool:
    config = load_config()
    llm_cfg = config.get("llm_gateway") if isinstance(config.get("llm_gateway"), dict) else {}
    if _as_bool(os.getenv(DEFAULT_ENABLED_ENV, "")):
        return True
    return _as_bool(llm_cfg.get("enabled", False))


_GLOBAL_GATEWAY: Optional[LLMGateway] = None
_GLOBAL_GATEWAY_CONFIG_PATH: str = ""


def is_gateway_enabled() -> bool:
    return _gateway_enabled_from_config()


def get_gateway() -> Optional[LLMGateway]:
    global _GLOBAL_GATEWAY
    global _GLOBAL_GATEWAY_CONFIG_PATH

    if not is_gateway_enabled():
        return None

    config_path = os.getenv(DEFAULT_CONFIG_ENV, "").strip()
    if not config_path:
        return None

    if _GLOBAL_GATEWAY is not None and _GLOBAL_GATEWAY_CONFIG_PATH == config_path:
        return _GLOBAL_GATEWAY

    cfg = _read_gateway_config(Path(config_path))
    if not cfg:
        return None

    _GLOBAL_GATEWAY = LLMGateway(cfg)
    _GLOBAL_GATEWAY_CONFIG_PATH = config_path
    return _GLOBAL_GATEWAY


def resolve_gateway_route(conversation_id: str, requested_model: str) -> Optional[Dict[str, Any]]:
    gateway = get_gateway()
    if not gateway:
        return None
    return gateway.resolve_gateway_route(conversation_id, requested_model)


def report_gateway_route_result(route_id: str, status_code: Optional[int] = None) -> None:
    gateway = get_gateway()
    if not gateway:
        return
    gateway.report_route_result(route_id, status_code=status_code)
