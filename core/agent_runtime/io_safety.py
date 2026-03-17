"""Safe stdio wrappers for long-running/headless agent execution."""

from __future__ import annotations

import sys
from typing import Any, TextIO


class SafeWriter:
    """Transparent stdio wrapper that catches OSError from broken pipes."""

    __slots__ = ("_inner",)

    def __init__(self, inner: TextIO):
        object.__setattr__(self, "_inner", inner)

    def write(self, data: str) -> int:
        try:
            return int(self._inner.write(data))
        except OSError:
            return len(data) if isinstance(data, str) else 0

    def flush(self) -> None:
        try:
            self._inner.flush()
        except OSError:
            pass

    def fileno(self) -> int:
        return int(self._inner.fileno())

    def isatty(self) -> bool:
        try:
            return bool(self._inner.isatty())
        except OSError:
            return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def install_safe_stdio() -> None:
    """Wrap stdout/stderr so best-effort console output cannot crash the agent."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and not isinstance(stream, SafeWriter):
            setattr(sys, stream_name, SafeWriter(stream))
