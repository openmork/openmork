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
from core.agent_runtime.turn_control import (
    build_api_messages_for_turn,
    process_final_response_without_tools,
    run_iteration_side_effects,
    setup_thinking_indicator,
    finalize_conversation_result,
    normalize_assistant_message_for_turn,
)


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
    assert "return _build_api_messages_for_turn_impl(" in source
    assert "return _process_final_response_without_tools_impl(" in source
    assert "return _run_iteration_side_effects_impl(self, messages=messages, api_call_count=api_call_count)" in source
    assert "return _setup_thinking_indicator_impl(" in source
    assert "return _finalize_conversation_result_impl(" in source
    assert "return _normalize_assistant_message_for_turn_impl(self, response)" in source
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


def test_turn_control_build_api_messages_for_turn_minimal_contract():
    agent = SimpleNamespace(
        _honcho_turn_context="ctx",
        base_url="https://openrouter.ai/api/v1",
        ephemeral_system_prompt="eph",
        prefill_messages=[{"role": "assistant", "content": "prefill"}],
        _use_prompt_caching=False,
        _cache_ttl="5m",
        context_compressor=SimpleNamespace(_sanitize_tool_pairs=lambda msgs: msgs),
        _sanitize_tool_calls_for_strict_api=lambda _msg: None,
    )
    out = build_api_messages_for_turn(
        agent,
        messages=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "ok", "reasoning": "r"}],
        current_turn_user_idx=0,
        active_system_prompt="sys",
    )
    assert out["api_messages"][0]["role"] == "system"
    assert out["api_messages"][1]["content"] == "prefill"
    assert "Honcho memory" in out["api_messages"][2]["content"]
    assert out["api_messages"][3]["reasoning_content"] == "r"
    assert out["approx_tokens"] >= 1


def test_turn_control_process_final_response_continue_on_codex_ack():
    saved_logs = {}
    agent = SimpleNamespace(
        _has_content_after_think_block=lambda _s: True,
        _looks_like_codex_intermediate_ack=lambda **_kwargs: True,
        _build_assistant_message=lambda _m, _f: {"role": "assistant", "content": "ack"},
        _strip_think_blocks=lambda s: s,
        _save_session_log=lambda msgs: saved_logs.setdefault("n", len(msgs)),
        _session_messages=[],
        api_mode="codex_responses",
        valid_tool_names={"x"},
        quiet_mode=True,
        log_prefix="",
        _vprint=lambda *_args, **_kwargs: None,
    )
    assistant_message = SimpleNamespace(content="I'll do that", tool_calls=None)
    out = process_final_response_without_tools(
        agent,
        assistant_message=assistant_message,
        finish_reason="stop",
        messages=[{"role": "user", "content": "u"}],
        user_message="u",
        codex_ack_continuations=0,
        truncated_response_prefix="",
        effective_task_id="t1",
        conversation_history=[],
        api_call_count=1,
    )
    assert out["action"] == "continue"
    assert out["codex_ack_continuations"] == 1


def test_turn_control_iteration_side_effects_and_indicator():
    step_calls = {}
    agent = SimpleNamespace(
        step_callback=lambda n, tools: step_calls.setdefault("args", (n, tools)),
        _skill_nudge_interval=1,
        valid_tool_names={"skill_manage"},
        _iters_since_skill=0,
        quiet_mode=False,
        log_prefix="",
        tools=[],
        _stream_callback=None,
        thinking_callback=None,
        verbose_logging=False,
        model="m",
        _vprint=lambda *_args, **_kwargs: None,
    )
    messages = [{"role": "assistant", "tool_calls": [{"function": {"name": "x"}}]}]
    run_iteration_side_effects(agent, messages=messages, api_call_count=2)
    assert step_calls["args"][0] == 2
    assert step_calls["args"][1] == ["x"]
    assert agent._iters_since_skill == 1

    indicator = setup_thinking_indicator(
        agent,
        api_call_count=2,
        max_iterations=8,
        api_messages=[{"role": "user", "content": "u"}],
        messages=[{"role": "user", "content": "u"}],
        approx_tokens=10,
        total_chars=40,
    )
    assert indicator is None


def test_turn_control_finalize_conversation_result_contract():
    calls = {}
    agent = SimpleNamespace(
        max_iterations=5,
        _save_trajectory=lambda *_args, **_kwargs: calls.setdefault("trajectory", True),
        _cleanup_task_resources=lambda tid: calls.setdefault("cleanup", tid),
        _persist_session=lambda *_args, **_kwargs: calls.setdefault("persist", True),
        _honcho_sync=lambda *_args, **_kwargs: calls.setdefault("honcho", True),
        _queue_honcho_prefetch=lambda *_args, **_kwargs: calls.setdefault("prefetch", True),
        _response_was_previewed=True,
        _interrupt_message=None,
        clear_interrupt=lambda: calls.setdefault("clear", True),
        _stream_callback=object(),
    )
    result = finalize_conversation_result(
        agent,
        messages=[{"role": "assistant", "content": "ok", "reasoning": "why"}],
        conversation_history=[],
        user_message="u",
        original_user_message="u",
        final_response="ok",
        api_call_count=1,
        interrupted=False,
        effective_task_id="t1",
    )
    assert result["completed"] is True
    assert result["last_reasoning"] == "why"
    assert calls["cleanup"] == "t1"
    assert agent._stream_callback is None


def test_turn_control_normalize_assistant_message_for_turn_contract():
    msg = SimpleNamespace(content={"text": "ok"}, tool_calls=None)
    resp = SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")])
    agent = SimpleNamespace(api_mode="chat_completions")
    assistant_message, finish_reason = normalize_assistant_message_for_turn(agent, resp)
    assert assistant_message.content == "ok"
    assert finish_reason == "stop"
