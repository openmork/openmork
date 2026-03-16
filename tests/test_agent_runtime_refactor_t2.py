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

    message = SimpleNamespace(reasoning="r1", reasoning_content="r2", reasoning_details=[{"summary": "r3"}])
    assert extract_reasoning_from_message(message) == "r1\n\nr2\n\nr3"
    assert inject_honcho_turn_context("hello", "ctx").endswith("ctx")
