from __future__ import annotations

from pathlib import Path

from scripts.ops.check_except_pass import scan_paths


def test_scan_paths_detects_except_pass(tmp_path: Path):
    target = tmp_path / "x.py"
    target.write_text("""try:\n    x = 1\nexcept Exception:\n    pass\n""", encoding="utf-8")

    hits = scan_paths([target])
    assert len(hits) == 1
    assert str(target) in hits[0]
