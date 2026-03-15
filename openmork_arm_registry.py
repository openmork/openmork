"""Central ARM registry with lightweight validation and observability."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from openmork_contracts import validate_arm_contract


Healthcheck = Callable[[Any], Any]


@dataclass
class ArmMetrics:
    calls: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        avg = self.total_latency_ms / self.calls if self.calls else 0.0
        return {
            "count": self.calls,
            "error": self.errors,
            "latency_ms_avg": round(avg, 3),
            "latency_ms_total": round(self.total_latency_ms, 3),
        }


@dataclass
class ArmRecord:
    arm_type: str
    arm: Any
    expected_api_version: str = "1.0"
    allow_legacy_api_version: bool = True
    compat: Optional[str] = None
    version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    healthcheck: Optional[Healthcheck] = None
    metrics: ArmMetrics = field(default_factory=ArmMetrics)
    last_health: Optional[dict[str, Any]] = None


class ArmRegistry:
    def __init__(self) -> None:
        self._records: dict[str, ArmRecord] = {}

    def register(
        self,
        arm_type: str,
        arm: Any,
        *,
        expected_api_version: str = "1.0",
        allow_legacy_api_version: bool = True,
        compat: Optional[str] = None,
        version: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        healthcheck: Optional[Healthcheck] = None,
    ) -> Any:
        validate_arm_contract(
            arm,
            arm_kind=arm_type,
            expected_api_version=expected_api_version,
            allow_legacy_api_version=allow_legacy_api_version,
        )
        self._records[arm_type] = ArmRecord(
            arm_type=arm_type,
            arm=arm,
            expected_api_version=expected_api_version,
            allow_legacy_api_version=allow_legacy_api_version,
            compat=compat,
            version=version,
            metadata=dict(metadata or {}),
            healthcheck=healthcheck,
        )
        return arm

    def resolve(self, arm_type: str, default: Any = None) -> Any:
        rec = self._records.get(arm_type)
        return rec.arm if rec else default

    def record_call(self, arm_type: str, *, latency_ms: float, error: bool = False) -> None:
        rec = self._records.get(arm_type)
        if not rec:
            return
        rec.metrics.calls += 1
        rec.metrics.total_latency_ms += max(0.0, float(latency_ms))
        if error:
            rec.metrics.errors += 1

    def run_healthcheck(self, arm_type: str) -> dict[str, Any]:
        rec = self._records.get(arm_type)
        if not rec:
            return {"ok": False, "reason": "arm_not_registered"}
        if rec.healthcheck is None:
            result = {"ok": True, "reason": "no_healthcheck"}
            rec.last_health = result
            return result

        start = time.perf_counter()
        ok = True
        payload: dict[str, Any] = {}
        try:
            raw = rec.healthcheck(rec.arm)
            if isinstance(raw, dict):
                payload = dict(raw)
                ok = bool(payload.get("ok", True))
            elif isinstance(raw, bool):
                ok = raw
            else:
                payload = {"value": raw}
        except Exception as exc:
            ok = False
            payload = {"error": str(exc)}
        latency_ms = (time.perf_counter() - start) * 1000.0
        self.record_call(arm_type, latency_ms=latency_ms, error=not ok)
        result = {"ok": ok, "latency_ms": round(latency_ms, 3), **payload}
        rec.last_health = result
        return result

    def dump_state(self) -> dict[str, Any]:
        arms: dict[str, Any] = {}
        for arm_type, rec in self._records.items():
            arms[arm_type] = {
                "apiVersion": getattr(rec.arm, "apiVersion", None),
                "expectedApiVersion": rec.expected_api_version,
                "compat": rec.compat,
                "version": rec.version,
                "metadata": rec.metadata,
                "metrics": rec.metrics.as_dict(),
                "health": rec.last_health,
            }
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "arms": arms,
        }

    def dump_json(self) -> str:
        return json.dumps(self.dump_state(), ensure_ascii=False, indent=2)


_registry_singleton: Optional[ArmRegistry] = None


def get_arm_registry() -> ArmRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = ArmRegistry()
    return _registry_singleton
