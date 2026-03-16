"""Regression coverage for T2 incremental run_agent split."""

from pathlib import Path
from types import SimpleNamespace

from core.agent_runtime.conversation_utils import (
    extract_reasoning_from_message,
    has_content_after_think_block,
    looks_like_codex_intermediate_ack,
    max_tokens_param,
    strip_think_blocks,
)
from core.agent_runtime.runtime_context import IterationBudget, inject_honcho_turn_context
from core.agent_runtime.api_client_helpers import build_api_kwargs, build_assistant_message
from core.agent_runtime.tool_execution import invoke_tool


def test_runtime_context_exports_keep_run_agent_compatibility():
    budget = IterationBudget(max_total=2)
    assert budget.consume() is True
    assert budget.consume() is True
    assert budget.consume() is False
    budget.refund()
    assert budget.remaining == 1


def test_conversation_utils_match_expected_behavior():
    assert max_tokens_param("https://api.openai.com/v1", 100) == {"max_completion_tokens": 100}
    assert max_tokens_param("https://openrouter.ai/api/v1", 100) == {"max_tokens": 100}

    assert has_content_after_think_block("<think>x</think> answer") is True
    assert has_content_after_think_block("<think>x</think>") is False
    assert strip_think_blocks("<think>hidden</think>show") == "show"

    ack = looks_like_codex_intermediate_ack(
        "check this repo",
        "I'll inspect the project and report back",
        [{"role": "user", "content": "check this repo"}],
    )
    assert ack is True


def test_run_agent_facade_references_extracted_helpers():
    source = Path("run_agent.py").read_text(encoding="utf-8")

    assert "inject_honcho_turn_context as _inject_honcho_turn_context" in source
    assert "return max_tokens_param(self.base_url, value)" in source
    assert "return has_content_after_think_block(content)" in source
    assert "return strip_think_blocks(content)" in source
    assert "return looks_like_codex_intermediate_ack(user_message, assistant_content, messages)" in source
    assert "return extract_reasoning_from_message(assistant_message)" in source
    assert "return _build_api_kwargs_impl(self, api_messages)" in source
    assert "return _execute_tool_calls_impl(self, assistant_message, messages, effective_task_id, api_call_count)" in source

    message = SimpleNamespace(reasoning="r1", reasoning_content="r2", reasoning_details=[{"summary": "r3"}])
    assert extract_reasoning_from_message(message) == "r1\n\nr2\n\nr3"
    assert inject_honcho_turn_context("hello", "ctx").endswith("ctx")


def test_api_helper_builders_minimal_contract():
    agent = SimpleNamespace(
        api_mode="codex_responses",
        reasoning_config=None,
        model="openai/gpt-5",
        session_id="sess-1",
        max_tokens=321,
        _chat_messages_to_responses_input=lambda payload: payload,
        _responses_tools=lambda: [{"type": "function", "name": "x", "parameters": {"type": "object"}}],
    )
    kwargs = build_api_kwargs(agent, [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}])
    assert kwargs["model"] == "openai/gpt-5"
    assert kwargs["instructions"] == "sys"
    assert kwargs["max_output_tokens"] == 321

    msg = SimpleNamespace(content="ok", tool_calls=None)
    out = build_assistant_message(SimpleNamespace(
        _extract_reasoning=lambda _m: None,
        verbose_logging=False,
        reasoning_callback=None,
    ), msg, "stop")
    assert out["content"] == "ok"
    assert out["finish_reason"] == "stop"


def test_tool_invoke_falls_back_to_handle_function_call(monkeypatch):
    calls = {}

    def _fake_handle(name, args, task_id, enabled_tools=None):
        calls["name"] = name
        calls["args"] = args
        calls["task_id"] = task_id
        calls["enabled_tools"] = enabled_tools
        return "ok"

    import sys
    import core.agent_runtime.tool_execution as te

    monkeypatch.setitem(sys.modules, "model_tools", SimpleNamespace(handle_function_call=_fake_handle))
    agent = SimpleNamespace(valid_tool_names={"x"})
    result = te.invoke_tool(agent, "x", {"a": 1}, "t1")
    assert result == "ok"
    assert calls["name"] == "x"
    assert calls["task_id"] == "t1"
