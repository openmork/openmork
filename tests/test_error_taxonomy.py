from __future__ import annotations

import json
import logging

from core.agent_runtime.error_taxonomy import ErrorCode, emit_error


def test_emit_error_writes_structured_json(caplog):
    logger = logging.getLogger("test.taxonomy")
    with caplog.at_level(logging.ERROR):
        envelope = emit_error(
            logger,
            code=ErrorCode.API_CALL_FAILED,
            message="request crashed",
            context={"provider": "openrouter", "attempt": 2},
        )

    assert envelope.code == ErrorCode.API_CALL_FAILED
    assert len(caplog.records) == 1

    payload = json.loads(caplog.records[0].message)
    assert payload["code"] == "api_call_failed"
    assert payload["message"] == "request crashed"
    assert payload["context"]["provider"] == "openrouter"


def test_emit_error_warning_level(caplog):
    logger = logging.getLogger("test.taxonomy.warning")
    with caplog.at_level(logging.WARNING):
        emit_error(
            logger,
            code=ErrorCode.TOOL_RESULT_ERROR,
            message="tool returned failure contract",
            context={"tool": "delegate_task"},
            severity="warning",
        )

    assert len(caplog.records) == 1
    payload = json.loads(caplog.records[0].message)
    assert payload["severity"] == "warning"
    assert payload["code"] == "tool_result_error"
