from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from openmork_cli.supply_chain import ensure_trusted_download_url, safe_extract_zip


def test_ensure_trusted_download_url_allows_github_https():
    ensure_trusted_download_url("https://github.com/openmork/openmork/archive/refs/heads/main.zip")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/openmork/openmork/archive/refs/heads/main.zip",
        "https://evil.example.com/archive.zip",
    ],
)
def test_ensure_trusted_download_url_blocks_untrusted(url: str):
    with pytest.raises(ValueError):
        ensure_trusted_download_url(url)


def test_safe_extract_zip_blocks_zip_slip(tmp_path: Path):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../escape.txt", "boom")

    with pytest.raises(ValueError):
        safe_extract_zip(zip_path, tmp_path / "out")


def test_safe_extract_zip_extracts_normal_archive(tmp_path: Path):
    zip_path = tmp_path / "ok.zip"
    out = tmp_path / "out"
    out.mkdir()
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("openmork-main/README.md", "ok")

    safe_extract_zip(zip_path, out)
    assert (out / "openmork-main" / "README.md").exists()
