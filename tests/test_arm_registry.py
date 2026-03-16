import json
import pytest

from openmork_arm_registry import ArmRegistry
from openmork_contracts import ArmContractError


class _GatewayArm:
    apiVersion = "1.0"

    def start(self):
        return None

    def stop(self):
        return None

    def send_message(self, session_id: str, content: str, **kwargs):
        return True

    def register_callback(self, handler):
        return None


def test_registry_register_and_resolve_gateway_arm():
    registry = ArmRegistry()
    arm = _GatewayArm()
    registry.register("gateway", arm, compat="stable", version="1.2.3")

    assert registry.resolve("gateway") is arm
    state = registry.dump_state()
    assert state["arms"]["gateway"]["compat"] == "stable"
    assert state["arms"]["gateway"]["version"] == "1.2.3"


def test_registry_rejects_invalid_contract():
    registry = ArmRegistry()
    with pytest.raises(ArmContractError):
        registry.register("gateway", object())


def test_registry_observability_health_and_metrics_smoke():
    registry = ArmRegistry()
    registry.register("gateway", _GatewayArm(), healthcheck=lambda _a: {"ok": True, "status": "healthy"})

    result = registry.run_healthcheck("gateway")
    assert result["ok"] is True

    registry.record_call("gateway", latency_ms=10.0)
    registry.record_call("gateway", latency_ms=5.0, error=True)

    payload = json.loads(registry.dump_json())
    metrics = payload["arms"]["gateway"]["metrics"]
    assert metrics["count"] >= 3
    assert metrics["error"] >= 1


def test_registry_integrates_security_arm_runtime_path():
    class _SecurityArm:
        apiVersion = "1.0"

        def validate_action(self, action_type: str, payload: dict, context: dict):
            ok = not str(payload.get("command", "")).startswith("rm -rf /")
            return type("V", (), {"is_allowed": ok, "reason": "blocked" if not ok else ""})()

    registry = ArmRegistry()
    arm = _SecurityArm()
    registry.register("security", arm, compat="guard")

    allowed = registry.resolve("security").validate_action(
        "terminal.command",
        {"command": "echo safe"},
        {"session_key": "test"},
    )
    assert getattr(allowed, "is_allowed", False) is True

def test_registry_integrates_skillset_arm_runtime_path():
    class _SkillsetArm:
        apiVersion = "1.0"

        @property
        def capabilities(self):
            return [{"name": "skills_list"}]

        def execute(self, tool_name: str, arguments: dict):
            if tool_name == "skills_list":
                return {"skills": ["demo"]}
            raise ValueError("unknown")

    registry = ArmRegistry()
    arm = _SkillsetArm()
    registry.register("skillset", arm, compat="builtin")

    skillset = registry.resolve("skillset")
    assert any(c.get("name") == "skills_list" for c in skillset.capabilities)
    payload = skillset.execute("skills_list", {})
    assert "skills" in payload
