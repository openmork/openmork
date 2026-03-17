from __future__ import annotations

from pathlib import Path

from scripts.ops.check_except_pass import collect_python_targets, scan_paths


def test_scan_paths_detects_except_pass(tmp_path: Path):
    target = tmp_path / "x.py"
    target.write_text("""try:\n    x = 1\nexcept Exception:\n    pass\n""", encoding="utf-8")

    hits = scan_paths([target])
    assert len(hits) == 1
    assert str(target) in hits[0]


def test_collect_python_targets_excludes_non_production_dirs(tmp_path: Path):
    app_file = tmp_path / "core" / "runtime.py"
    test_file = tmp_path / "tests" / "test_runtime.py"
    docs_file = tmp_path / "docs" / "snippet.py"

    app_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.parent.mkdir(parents=True, exist_ok=True)
    docs_file.parent.mkdir(parents=True, exist_ok=True)

    app_file.write_text("print('ok')\n", encoding="utf-8")
    test_file.write_text("print('test')\n", encoding="utf-8")
    docs_file.write_text("print('docs')\n", encoding="utf-8")

    targets = collect_python_targets(tmp_path)
    assert app_file in targets
    assert test_file not in targets
    assert docs_file not in targets
