"""Supply-chain guards for network downloads and archive extraction."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import zipfile

_ALLOWED_HTTPS_HOSTS = {
    "github.com",
    "codeload.github.com",
    "raw.githubusercontent.com",
}


def ensure_trusted_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Untrusted download URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HTTPS_HOSTS:
        raise ValueError(f"Untrusted download host: {host!r}")


def _safe_target_path(dest_dir: Path, member_name: str) -> Path:
    target = (dest_dir / member_name).resolve()
    root = dest_dir.resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"Blocked archive path traversal entry: {member_name}")
    return target


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """Extract ZIP contents after validating members against zip-slip traversal."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            _safe_target_path(dest_dir, member.filename)
        zf.extractall(dest_dir)
