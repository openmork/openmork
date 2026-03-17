"""Core runtime error taxonomy + structured observability helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from typing import Any, Mapping


class ErrorCode(str, Enum):
    API_CALL_INTERRUPTED = "api_call_interrupted"
    API_CALL_FAILED = "api_call_failed"
    API_STREAM_FAILED = "api_stream_failed"
    TOOL_INVOKE_FAILED = "tool_invoke_failed"
    TOOL_RESULT_ERROR = "tool_result_error"
    CHECKPOINT_PRESAVE_FAILED = "checkpoint_presave_failed"


@dataclass(frozen=True)
class ErrorEnvelope:
    code: ErrorCode
    message: str
    context: Mapping[str, Any]
    severity: str = "error"

    def to_payload(self) -> dict[str, Any]:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "code": self.code.value,
            "severity": self.severity,
            "message": self.message,
            "context": dict(self.context),
        }


def emit_error(
    logger: logging.Logger,
    *,
    code: ErrorCode,
    message: str,
    context: Mapping[str, Any] | None = None,
    severity: str = "error",
    exc_info: bool = False,
) -> ErrorEnvelope:
    envelope = ErrorEnvelope(
        code=code,
        message=message,
        context=context or {},
        severity=severity,
    )
    payload = envelope.to_payload()
    log_line = json.dumps(payload, ensure_ascii=False)
    level = severity.lower().strip()
    if level == "warning":
        logger.warning(log_line, exc_info=exc_info)
    elif level == "info":
        logger.info(log_line, exc_info=exc_info)
    else:
        logger.error(log_line, exc_info=exc_info)
    return envelope
