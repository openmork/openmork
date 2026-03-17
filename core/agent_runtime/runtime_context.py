"""Runtime context/state helpers extracted from ``run_agent.py``.

These utilities are intentionally stateless wrappers to keep the
``run_agent`` public surface backward compatible while allowing incremental
modularization.
"""

from __future__ import annotations

import threading
from typing import Any


class IterationBudget:
    """Thread-safe shared iteration counter for parent and child agents."""

    def __init__(self, max_total: int):
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)


def inject_honcho_turn_context(content: Any, turn_context: str) -> Any:
    """Append Honcho recall to current-turn user message without mutating history."""
    if not turn_context:
        return content

    note = (
        "[System note: The following Honcho memory was retrieved from prior "
        "sessions. It is continuity context for this turn only, not new user "
        "input.]\n\n"
        f"{turn_context}"
    )

    if isinstance(content, list):
        return list(content) + [{"type": "text", "text": note}]

    text = "" if content is None else str(content)
    if not text.strip():
        return note
    return f"{text}\n\n{note}"
