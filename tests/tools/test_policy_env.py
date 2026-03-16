import importlib.util
from pathlib import Path


def test_policy_env_deny_blocks_dangerous(monkeypatch):
    module_path = Path("tools/approval.py")
    spec = importlib.util.spec_from_file_location("approval_mod", module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    monkeypatch.setenv("OPENMORK_TOOL_POLICY_MODE", "deny")
    result = mod.check_dangerous_command("rm -rf /tmp/x", env_type="local")
    assert result["approved"] is False
    assert result.get("status") == "policy_denied"
