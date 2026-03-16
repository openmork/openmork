import json
import sys
import types
from types import SimpleNamespace


def test_show_status_arms_reads_registry_dump(monkeypatch, capsys, tmp_path):
    sys.modules.setdefault("httpx", types.SimpleNamespace(get=lambda *a, **k: None))
    from openmork_cli import status as status_mod

    home = tmp_path / ".openmork"
    reports = home / "reports"
    reports.mkdir(parents=True)
    arm_file = reports / "arm_registry_status.json"
    arm_file.write_text(
        json.dumps(
            {
                "timestamp": "2026-03-16T00:00:00+00:00",
                "arms": {
                    "security": {
                        "metrics": {"count": 2, "error": 1, "latency_ms_avg": 12.3},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("OPENMORK_HOME", str(home))
    monkeypatch.setattr(status_mod, "get_openmork_home", lambda: home, raising=False)
    monkeypatch.setattr(
        status_mod.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="inactive\n", returncode=3),
    )

    status_mod.show_status(SimpleNamespace(all=False, deep=False, arms=True))
    out = capsys.readouterr().out

    assert "ARM Registry" in out
    assert "security" in out
    assert "count=2" in out
