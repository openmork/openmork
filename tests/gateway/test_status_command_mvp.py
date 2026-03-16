from pathlib import Path


def test_status_command_mentions_mvp_fields():
    src = Path("gateway/run.py").read_text(encoding="utf-8")
    assert "**Model:**" in src
    assert "**Context (last prompt):**" in src
    assert "**Estimated Cost:**" in src
    assert "**Queue (approx):**" in src
