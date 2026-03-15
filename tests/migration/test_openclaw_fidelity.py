import importlib.util
import json
import sys
from pathlib import Path

import yaml


def _load_migration_module(repo_root: Path):
    script_path = (
        repo_root
        / "optional-skills"
        / "migration"
        / "openclaw-migration"
        / "scripts"
        / "openclaw_to_openmork.py"
    )
    spec = importlib.util.spec_from_file_location("openclaw_to_openmork", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module at {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _create_openclaw_fixture(base_dir: Path) -> Path:
    source = base_dir / ".openclaw"
    workspace = source / "workspace"
    workspace.mkdir(parents=True)

    openclaw_config = {
        "agents": {"defaults": {"model": "openrouter/anthropic/claude-3.5-sonnet"}},
        "models": {"providers": {"openrouter": {"apiKey": "sk-test-openrouter"}}},
    }
    (source / "openclaw.json").write_text(json.dumps(openclaw_config), encoding="utf-8")
    (workspace / "SOUL.md").write_text(
        "# Soul\nYou are Chytzo's elite execution partner.", encoding="utf-8"
    )
    skill_dir = workspace / "skills" / "mock_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: mock_skill\ndescription: mock migration skill\n---\n# Mock Skill\n", encoding="utf-8"
    )
    return source


def test_openclaw_migration_full_fidelity(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    module = _load_migration_module(repo_root)

    source_root = _create_openclaw_fixture(tmp_path)
    target_root = tmp_path / ".openmork"
    workspace_target = target_root / "workspace"
    target_root.mkdir()
    workspace_target.mkdir(parents=True)

    (target_root / "config.yaml").write_text("agent:\n  max_turns: 100\n", encoding="utf-8")

    selected = module.resolve_selected_options(None, None, preset="full")
    migrator = module.Migrator(
        source_root=source_root,
        target_root=target_root,
        execute=True,
        workspace_target=workspace_target,
        overwrite=True,
        migrate_secrets=True,
        output_dir=None,
        selected_options=selected,
        preset_name="full",
    )

    report = migrator.migrate()
    assert report["summary"]["error"] == 0

    # 1) Base config fidelity
    config = yaml.safe_load((target_root / "config.yaml").read_text(encoding="utf-8"))
    assert config.get("agent", {}).get("max_turns") == 100
    assert config.get("model") == "openrouter/anthropic/claude-3.5-sonnet"

    # 2) Identity/persona fidelity (OpenClaw SOUL -> OpenMork SOUL)
    soul_path = target_root / "SOUL.md"
    assert soul_path.exists(), "Expected SOUL file to be migrated"
    assert "elite execution partner" in soul_path.read_text(encoding="utf-8")

    # 3) Skills fidelity
    migrated_skill = target_root / "skills" / "openclaw-imports" / "mock_skill" / "SKILL.md"
    assert migrated_skill.exists(), "Expected skill to be migrated under openclaw-imports"
    assert "Mock Skill" in migrated_skill.read_text(encoding="utf-8")
