"""Gateway watchdog + minimal auto-healing signals.

Tracks repeated auth/rate-limit errors and exposes trigger state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict


@dataclass
class WatchdogConfig:
    window_seconds: int = 300
    threshold_401: int = 3
    threshold_429: int = 4


@dataclass
class GatewayWatchdog:
    cfg: WatchdogConfig = field(default_factory=WatchdogConfig)
    _events_401: Deque[datetime] = field(default_factory=deque)
    _events_429: Deque[datetime] = field(default_factory=deque)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _trim(self, bucket: Deque[datetime], now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.cfg.window_seconds)
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

    def record_error_code(self, code: str) -> None:
        now = self._now()
        if str(code) == "401":
            self._events_401.append(now)
            self._trim(self._events_401, now)
        elif str(code) == "429":
            self._events_429.append(now)
            self._trim(self._events_429, now)

    def snapshot(self) -> Dict[str, int | bool | str]:
        now = self._now()
        self._trim(self._events_401, now)
        self._trim(self._events_429, now)
        c401 = len(self._events_401)
        c429 = len(self._events_429)
        return {
            "window_seconds": self.cfg.window_seconds,
            "errors_401": c401,
            "errors_429": c429,
            "trigger_401": c401 >= self.cfg.threshold_401,
            "trigger_429": c429 >= self.cfg.threshold_429,
            "action": self.recommended_action(),
        }

    def recommended_action(self) -> str:
        now = self._now()
        self._trim(self._events_401, now)
        self._trim(self._events_429, now)
        if len(self._events_401) >= self.cfg.threshold_401:
            return "reauth_required"
        if len(self._events_429) >= self.cfg.threshold_429:
            return "rate_limit_backoff"
        return "ok"
