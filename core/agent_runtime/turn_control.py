"""Turn-loop helpers extracted from run_agent.AIAgent (T2 cut 3)."""

from __future__ import annotations

import logging
import random

from agent.display import KawaiiSpinner
from agent.prompt_caching import apply_anthropic_cache_control
from core.agent_runtime.runtime_context import inject_honcho_turn_context


logger = logging.getLogger(__name__)


def build_api_messages_for_turn(
    agent,
    *,
    messages: list,
    current_turn_user_idx: int,
    active_system_prompt: str,
):
    """Prepare API payload messages for one loop iteration."""
    api_messages = []
    for idx, msg in enumerate(messages):
        api_msg = msg.copy()

        if idx == current_turn_user_idx and msg.get("role") == "user" and agent._honcho_turn_context:
            api_msg["content"] = inject_honcho_turn_context(
                api_msg.get("content", ""), agent._honcho_turn_context
            )

        if msg.get("role") == "assistant":
            reasoning_text = msg.get("reasoning")
            if reasoning_text:
                api_msg["reasoning_content"] = reasoning_text

        if "reasoning" in api_msg:
            api_msg.pop("reasoning")
        if "finish_reason" in api_msg:
            api_msg.pop("finish_reason")

        if "api.mistral.ai" in agent.base_url.lower():
            agent._sanitize_tool_calls_for_strict_api(api_msg)

        api_messages.append(api_msg)

    effective_system = active_system_prompt or ""
    if agent.ephemeral_system_prompt:
        effective_system = (effective_system + "\n\n" + agent.ephemeral_system_prompt).strip()
    if effective_system:
        api_messages = [{"role": "system", "content": effective_system}] + api_messages

    if agent.prefill_messages:
        sys_offset = 1 if effective_system else 0
        for idx, pfm in enumerate(agent.prefill_messages):
            api_messages.insert(sys_offset + idx, pfm.copy())

    if agent._use_prompt_caching:
        api_messages = apply_anthropic_cache_control(api_messages, cache_ttl=agent._cache_ttl)

    if hasattr(agent, "context_compressor") and agent.context_compressor:
        api_messages = agent.context_compressor._sanitize_tool_pairs(api_messages)

    total_chars = sum(len(str(msg)) for msg in api_messages)
    approx_tokens = total_chars // 4

    return {
        "api_messages": api_messages,
        "effective_system": effective_system,
        "total_chars": total_chars,
        "approx_tokens": approx_tokens,
    }


def run_iteration_side_effects(agent, *, messages: list, api_call_count: int) -> None:
    """Run per-iteration callbacks/counters before API payload build."""
    if agent.step_callback is not None:
        try:
            prev_tools = []
            for _m in reversed(messages):
                if _m.get("role") == "assistant" and _m.get("tool_calls"):
                    prev_tools = [
                        tc["function"]["name"]
                        for tc in _m["tool_calls"]
                        if isinstance(tc, dict)
                    ]
                    break
            agent.step_callback(api_call_count, prev_tools)
        except Exception as _step_err:
            logger.debug("step_callback error (iteration %s): %s", api_call_count, _step_err)

    if (agent._skill_nudge_interval > 0 and "skill_manage" in agent.valid_tool_names):
        agent._iters_since_skill += 1


def setup_thinking_indicator(
    agent,
    *,
    api_call_count: int,
    max_iterations: int,
    api_messages: list,
    messages: list,
    approx_tokens: int,
    total_chars: int,
):
    """Emit turn diagnostics and maybe start quiet-mode spinner."""
    thinking_spinner = None
    if not agent.quiet_mode:
        agent._vprint(f"\n{agent.log_prefix}🔄 Making API call #{api_call_count}/{max_iterations}...")
        agent._vprint(f"{agent.log_prefix}   📊 Request size: {len(api_messages)} messages, ~{approx_tokens:,} tokens (~{total_chars:,} chars)")
        agent._vprint(f"{agent.log_prefix}   🔧 Available tools: {len(agent.tools) if agent.tools else 0}")
    elif getattr(agent, "_stream_callback", None) is None:
        face = random.choice(KawaiiSpinner.KAWAII_THINKING)
        verb = random.choice(KawaiiSpinner.THINKING_VERBS)
        if agent.thinking_callback:
            agent.thinking_callback(f"{face} {verb}...")
        else:
            spinner_type = random.choice(["brain", "sparkle", "pulse", "moon", "star"])
            thinking_spinner = KawaiiSpinner(f"{face} {verb}...", spinner_type=spinner_type)
            thinking_spinner.start()

    if agent.verbose_logging:
        logging.debug(
            "API Request - Model: %s, Messages: %s, Tools: %s",
            agent.model,
            len(messages),
            len(agent.tools) if agent.tools else 0,
        )
        logging.debug("Last message role: %s", messages[-1]["role"] if messages else "none")
        logging.debug("Total message size: ~%s tokens", f"{approx_tokens:,}")

    return thinking_spinner


def normalize_assistant_message_for_turn(agent, response):
    """Normalize provider-specific response into assistant_message + finish_reason."""
    if agent.api_mode == "codex_responses":
        assistant_message, finish_reason = agent._normalize_codex_response(response)
    elif agent.api_mode == "anthropic_messages":
        from agent.anthropic_adapter import normalize_anthropic_response

        assistant_message, finish_reason = normalize_anthropic_response(response)
    else:
        assistant_message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

    if assistant_message.content is not None and not isinstance(assistant_message.content, str):
        raw = assistant_message.content
        if isinstance(raw, dict):
            assistant_message.content = raw.get("text", "") or raw.get("content", "") or str(raw)
        elif isinstance(raw, list):
            parts = []
            for part in raw:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif isinstance(part, dict) and "text" in part:
                    parts.append(str(part["text"]))
            assistant_message.content = "\n".join(parts)
        else:
            assistant_message.content = str(raw)

    return assistant_message, finish_reason


def finalize_conversation_result(
    agent,
    *,
    messages: list,
    conversation_history: list,
    user_message: str,
    original_user_message: str,
    final_response,
    api_call_count: int,
    interrupted: bool,
    effective_task_id: str,
):
    """Finalize persistence/sync and build the run_conversation result dict."""
    completed = final_response is not None and api_call_count < agent.max_iterations

    agent._save_trajectory(messages, user_message, completed)
    agent._cleanup_task_resources(effective_task_id)
    agent._persist_session(messages, conversation_history)

    if final_response and not interrupted:
        agent._honcho_sync(original_user_message, final_response)
        agent._queue_honcho_prefetch(original_user_message)

    last_reasoning = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("reasoning"):
            last_reasoning = msg["reasoning"]
            break

    result = {
        "final_response": final_response,
        "last_reasoning": last_reasoning,
        "messages": messages,
        "api_calls": api_call_count,
        "completed": completed,
        "partial": False,
        "interrupted": interrupted,
        "response_previewed": getattr(agent, "_response_was_previewed", False),
    }
    agent._response_was_previewed = False

    if interrupted and agent._interrupt_message:
        result["interrupt_message"] = agent._interrupt_message

    agent.clear_interrupt()
    agent._stream_callback = None

    return result


def process_final_response_without_tools(
    agent,
    *,
    assistant_message,
    finish_reason: str,
    messages: list,
    user_message: str,
    codex_ack_continuations: int,
    truncated_response_prefix: str,
    effective_task_id: str,
    conversation_history: list,
    api_call_count: int,
):
    """Handle no-tool assistant turn and decide loop control."""
    final_response = assistant_message.content or ""

    if not agent._has_content_after_think_block(final_response):
        fallback = getattr(agent, "_last_content_with_tools", None)
        if fallback:
            logger.debug("Empty follow-up after tool calls — using prior turn content as final response")
            agent._last_content_with_tools = None
            agent._empty_content_retries = 0
            for i in range(len(messages) - 1, -1, -1):
                msg = messages[i]
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    tool_names = []
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        tool_names.append(fn.get("name", "unknown"))
                    msg["content"] = f"Calling the {', '.join(tool_names)} tool{'s' if len(tool_names) > 1 else ''}..."
                    break
            final_response = agent._strip_think_blocks(fallback).strip()
            agent._response_was_previewed = True
            return {
                "action": "final",
                "final_response": final_response,
                "codex_ack_continuations": codex_ack_continuations,
            }

        if not hasattr(agent, "_empty_content_retries"):
            agent._empty_content_retries = 0
        agent._empty_content_retries += 1

        reasoning_text = agent._extract_reasoning(assistant_message)
        agent._vprint(f"{agent.log_prefix}⚠️  Response only contains think block with no content after it")
        if reasoning_text:
            reasoning_preview = reasoning_text[:500] + "..." if len(reasoning_text) > 500 else reasoning_text
            agent._vprint(f"{agent.log_prefix}   Reasoning: {reasoning_preview}")
        else:
            content_preview = final_response[:80] + "..." if len(final_response) > 80 else final_response
            agent._vprint(f"{agent.log_prefix}   Content: '{content_preview}'")

        if agent._empty_content_retries < 3:
            agent._vprint(f"{agent.log_prefix}🔄 Retrying API call ({agent._empty_content_retries}/3)...")
            return {
                "action": "continue",
                "final_response": None,
                "codex_ack_continuations": codex_ack_continuations,
            }

        agent._vprint(f"{agent.log_prefix}❌ Max retries (3) for empty content exceeded.", force=True)
        agent._empty_content_retries = 0

        fallback = getattr(agent, "_last_content_with_tools", None)
        if fallback:
            agent._last_content_with_tools = None
            for i in range(len(messages) - 1, -1, -1):
                msg = messages[i]
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    tool_names = []
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        tool_names.append(fn.get("name", "unknown"))
                    msg["content"] = f"Calling the {', '.join(tool_names)} tool{'s' if len(tool_names) > 1 else ''}..."
                    break
            final_response = agent._strip_think_blocks(fallback).strip()
            agent._response_was_previewed = True
            return {
                "action": "final",
                "final_response": final_response,
                "codex_ack_continuations": codex_ack_continuations,
            }

        empty_msg = {
            "role": "assistant",
            "content": final_response,
            "reasoning": reasoning_text,
            "finish_reason": finish_reason,
        }
        messages.append(empty_msg)

        agent._cleanup_task_resources(effective_task_id)
        agent._persist_session(messages, conversation_history)

        return {
            "action": "return",
            "result": {
                "final_response": final_response or None,
                "messages": messages,
                "api_calls": api_call_count,
                "completed": False,
                "partial": True,
                "error": "Model generated only think blocks with no actual response after 3 retries",
            },
            "codex_ack_continuations": codex_ack_continuations,
        }

    if hasattr(agent, "_empty_content_retries"):
        agent._empty_content_retries = 0

    if (
        agent.api_mode == "codex_responses"
        and agent.valid_tool_names
        and codex_ack_continuations < 2
        and agent._looks_like_codex_intermediate_ack(
            user_message=user_message,
            assistant_content=final_response,
            messages=messages,
        )
    ):
        codex_ack_continuations += 1
        interim_msg = agent._build_assistant_message(assistant_message, "incomplete")
        messages.append(interim_msg)

        continue_msg = {
            "role": "user",
            "content": (
                "[System: Continue now. Execute the required tool calls and only "
                "send your final answer after completing the task.]"
            ),
        }
        messages.append(continue_msg)
        agent._session_messages = messages
        agent._save_session_log(messages)
        return {
            "action": "continue",
            "final_response": None,
            "codex_ack_continuations": codex_ack_continuations,
        }

    codex_ack_continuations = 0

    if truncated_response_prefix:
        final_response = truncated_response_prefix + final_response

    final_response = agent._strip_think_blocks(final_response).strip()
    final_msg = agent._build_assistant_message(assistant_message, finish_reason)
    messages.append(final_msg)

    if not agent.quiet_mode:
        print(f"🎉 Conversation completed after {api_call_count} OpenAI-compatible API call(s)")

    return {
        "action": "final",
        "final_response": final_response,
        "codex_ack_continuations": codex_ack_continuations,
    }
