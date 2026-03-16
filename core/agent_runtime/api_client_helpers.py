"""API/client helper functions extracted from run_agent.AIAgent (T2)."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from types import SimpleNamespace

from agent.prompt_builder import DEFAULT_AGENT_IDENTITY


logger = logging.getLogger(__name__)


def interruptible_api_call(agent, api_kwargs: dict):
    """Run one API call in a background thread so interrupts can abort quickly."""
    result = {"response": None, "error": None}
    request_client_holder = {"client": None}

    def _call():
        try:
            if agent.api_mode == "codex_responses":
                request_client_holder["client"] = agent._create_request_openai_client(reason="codex_stream_request")
                result["response"] = agent._run_codex_stream(
                    api_kwargs,
                    client=request_client_holder["client"],
                )
            elif agent.api_mode == "anthropic_messages":
                result["response"] = agent._anthropic_messages_create(api_kwargs)
            else:
                request_client_holder["client"] = agent._create_request_openai_client(reason="chat_completion_request")
                result["response"] = request_client_holder["client"].chat.completions.create(**api_kwargs)
        except Exception as e:
            result["error"] = e
        finally:
            request_client = request_client_holder.get("client")
            if request_client is not None:
                agent._close_request_openai_client(request_client, reason="request_complete")

    t = threading.Thread(target=_call, daemon=True)
    t.start()
    while t.is_alive():
        t.join(timeout=0.3)
        if agent._interrupt_requested:
            try:
                if agent.api_mode == "anthropic_messages":
                    from agent.anthropic_adapter import build_anthropic_client

                    agent._anthropic_client.close()
                    agent._anthropic_client = build_anthropic_client(
                        agent._anthropic_api_key,
                        getattr(agent, "_anthropic_base_url", None),
                    )
                else:
                    request_client = request_client_holder.get("client")
                    if request_client is not None:
                        agent._close_request_openai_client(request_client, reason="interrupt_abort")
            except Exception as e:
                logger.warning("Interrupt cleanup failed while aborting API call: %s", e)
            raise InterruptedError("Agent interrupted during API call")
    if result["error"] is not None:
        raise result["error"]
    return result["response"]


def streaming_api_call(agent, api_kwargs: dict, stream_callback):
    """Streaming variant used by voice/TTS pipeline."""
    result = {"response": None, "error": None}
    request_client_holder = {"client": None}

    def _call():
        try:
            stream_kwargs = {**api_kwargs, "stream": True}
            request_client_holder["client"] = agent._create_request_openai_client(
                reason="chat_completion_stream_request"
            )
            stream = request_client_holder["client"].chat.completions.create(**stream_kwargs)

            content_parts: list[str] = []
            tool_calls_acc: dict[int, dict] = {}
            finish_reason = None
            model_name = None
            role = "assistant"

            for chunk in stream:
                if not chunk.choices:
                    if hasattr(chunk, "model") and chunk.model:
                        model_name = chunk.model
                    continue

                delta = chunk.choices[0].delta
                if hasattr(chunk, "model") and chunk.model:
                    model_name = chunk.model

                if delta and delta.content:
                    content_parts.append(delta.content)
                    try:
                        stream_callback(delta.content)
                    except Exception as e:
                        logger.debug("stream_callback failed for content chunk: %s", e)

                if delta and delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index if tc_delta.index is not None else 0
                        if idx in tool_calls_acc and tc_delta.id and tc_delta.id != tool_calls_acc[idx]["id"]:
                            matched = False
                            for eidx, eentry in tool_calls_acc.items():
                                if eentry["id"] == tc_delta.id:
                                    idx = eidx
                                    matched = True
                                    break
                            if not matched:
                                idx = (max(k for k in tool_calls_acc if isinstance(k, int)) + 1) if tool_calls_acc else 0
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc_delta.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        entry = tool_calls_acc[idx]
                        if tc_delta.id:
                            entry["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                entry["function"]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                entry["function"]["arguments"] += tc_delta.function.arguments

                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

            full_content = "".join(content_parts) or None
            mock_tool_calls = None
            if tool_calls_acc:
                mock_tool_calls = []
                for idx in sorted(tool_calls_acc):
                    tc = tool_calls_acc[idx]
                    mock_tool_calls.append(SimpleNamespace(
                        id=tc["id"],
                        type=tc["type"],
                        function=SimpleNamespace(
                            name=tc["function"]["name"],
                            arguments=tc["function"]["arguments"],
                        ),
                    ))

            mock_message = SimpleNamespace(
                role=role,
                content=full_content,
                tool_calls=mock_tool_calls,
                reasoning_content=None,
            )
            mock_choice = SimpleNamespace(
                index=0,
                message=mock_message,
                finish_reason=finish_reason or "stop",
            )
            mock_response = SimpleNamespace(
                id="stream-" + str(uuid.uuid4()),
                model=model_name,
                choices=[mock_choice],
                usage=None,
            )
            result["response"] = mock_response

        except Exception as e:
            result["error"] = e
        finally:
            request_client = request_client_holder.get("client")
            if request_client is not None:
                agent._close_request_openai_client(request_client, reason="stream_request_complete")

    t = threading.Thread(target=_call, daemon=True)
    t.start()
    while t.is_alive():
        t.join(timeout=0.3)
        if agent._interrupt_requested:
            try:
                if agent.api_mode == "anthropic_messages":
                    from agent.anthropic_adapter import build_anthropic_client

                    agent._anthropic_client.close()
                    agent._anthropic_client = build_anthropic_client(
                        agent._anthropic_api_key,
                        getattr(agent, "_anthropic_base_url", None),
                    )
                else:
                    request_client = request_client_holder.get("client")
                    if request_client is not None:
                        agent._close_request_openai_client(request_client, reason="stream_interrupt_abort")
            except Exception as e:
                logger.warning("Interrupt cleanup failed while aborting stream API call: %s", e)
            raise InterruptedError("Agent interrupted during API call")
    if result["error"] is not None:
        raise result["error"]
    return result["response"]


def build_api_kwargs(agent, api_messages: list) -> dict:
    """Build request kwargs for active API mode."""
    if agent.api_mode == "anthropic_messages":
        from agent.anthropic_adapter import build_anthropic_kwargs
        anthropic_messages = agent._prepare_anthropic_messages_for_api(api_messages)
        return build_anthropic_kwargs(
            model=agent.model,
            messages=anthropic_messages,
            tools=agent.tools,
            max_tokens=agent.max_tokens,
            reasoning_config=agent.reasoning_config,
        )

    if agent.api_mode == "codex_responses":
        instructions = ""
        payload_messages = api_messages
        if api_messages and api_messages[0].get("role") == "system":
            instructions = str(api_messages[0].get("content") or "").strip()
            payload_messages = api_messages[1:]
        if not instructions:
            instructions = DEFAULT_AGENT_IDENTITY

        reasoning_effort = "medium"
        reasoning_enabled = True
        if agent.reasoning_config and isinstance(agent.reasoning_config, dict):
            if agent.reasoning_config.get("enabled") is False:
                reasoning_enabled = False
            elif agent.reasoning_config.get("effort"):
                reasoning_effort = agent.reasoning_config["effort"]

        kwargs = {
            "model": agent.model,
            "instructions": instructions,
            "input": agent._chat_messages_to_responses_input(payload_messages),
            "tools": agent._responses_tools(),
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "store": False,
            "prompt_cache_key": agent.session_id,
        }

        if reasoning_enabled:
            kwargs["reasoning"] = {"effort": reasoning_effort, "summary": "auto"}
            kwargs["include"] = ["reasoning.encrypted_content"]
        else:
            kwargs["include"] = []

        if agent.max_tokens is not None:
            kwargs["max_output_tokens"] = agent.max_tokens

        return kwargs

    sanitized_messages = api_messages
    needs_sanitization = False
    for msg in api_messages:
        if not isinstance(msg, dict):
            continue
        if "codex_reasoning_items" in msg:
            needs_sanitization = True
            break

        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                if "call_id" in tool_call or "response_item_id" in tool_call:
                    needs_sanitization = True
                    break
            if needs_sanitization:
                break

    if needs_sanitization:
        import copy

        sanitized_messages = copy.deepcopy(api_messages)
        for msg in sanitized_messages:
            if not isinstance(msg, dict):
                continue
            msg.pop("codex_reasoning_items", None)
            tool_calls = msg.get("tool_calls")
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict):
                        tool_call.pop("call_id", None)
                        tool_call.pop("response_item_id", None)

    provider_preferences = {}
    if agent.providers_allowed:
        provider_preferences["only"] = agent.providers_allowed
    if agent.providers_ignored:
        provider_preferences["ignore"] = agent.providers_ignored
    if agent.providers_order:
        provider_preferences["order"] = agent.providers_order
    if agent.provider_sort:
        provider_preferences["sort"] = agent.provider_sort
    if agent.provider_require_parameters:
        provider_preferences["require_parameters"] = True
    if agent.provider_data_collection:
        provider_preferences["data_collection"] = agent.provider_data_collection

    api_kwargs = {
        "model": agent.model,
        "messages": sanitized_messages,
        "tools": agent.tools if agent.tools else None,
        "timeout": float(__import__('os').getenv("OPENMORK_API_TIMEOUT", 900.0)),
    }

    if agent.max_tokens is not None:
        api_kwargs.update(agent._max_tokens_param(agent.max_tokens))

    extra_body = {}

    _is_openrouter = "openrouter" in agent.base_url.lower()
    if provider_preferences and _is_openrouter:
        extra_body["provider"] = provider_preferences
    _is_nous = "nousresearch" in agent.base_url.lower()

    _is_mistral = "api.mistral.ai" in agent.base_url.lower()
    if (_is_openrouter or _is_nous) and not _is_mistral:
        if agent.reasoning_config is not None:
            rc = dict(agent.reasoning_config)
            if _is_nous and rc.get("enabled") is False:
                pass
            else:
                extra_body["reasoning"] = rc
        else:
            extra_body["reasoning"] = {
                "enabled": True,
                "effort": "medium"
            }

    if _is_nous:
        extra_body["tags"] = ["product=openmork"]

    if extra_body:
        api_kwargs["extra_body"] = extra_body

    return api_kwargs


def build_assistant_message(agent, assistant_message, finish_reason: str) -> dict:
    """Normalize API assistant message to run_agent internal dict shape."""
    import re

    reasoning_text = agent._extract_reasoning(assistant_message)
    if not reasoning_text:
        content = assistant_message.content or ""
        think_blocks = re.findall(r'<think>(.*?)</think>', content, flags=re.DOTALL)
        if think_blocks:
            combined = "\n\n".join(b.strip() for b in think_blocks if b.strip())
            reasoning_text = combined or None

    if reasoning_text and agent.verbose_logging:
        preview = reasoning_text[:100] + "..." if len(reasoning_text) > 100 else reasoning_text
        logging.debug(f"Captured reasoning ({len(reasoning_text)} chars): {preview}")

    if reasoning_text and agent.reasoning_callback:
        try:
            agent.reasoning_callback(reasoning_text)
        except Exception:
            pass

    msg = {
        "role": "assistant",
        "content": assistant_message.content or "",
        "reasoning": reasoning_text,
        "finish_reason": finish_reason,
    }

    if hasattr(assistant_message, 'reasoning_details') and assistant_message.reasoning_details:
        raw_details = assistant_message.reasoning_details
        preserved = []
        for d in raw_details:
            if isinstance(d, dict):
                preserved.append(d)
            elif hasattr(d, "__dict__"):
                preserved.append(d.__dict__)
            elif hasattr(d, "model_dump"):
                preserved.append(d.model_dump())
        if preserved:
            msg["reasoning_details"] = preserved

    codex_items = getattr(assistant_message, "codex_reasoning_items", None)
    if codex_items:
        msg["codex_reasoning_items"] = codex_items

    if assistant_message.tool_calls:
        tool_calls = []
        for tool_call in assistant_message.tool_calls:
            raw_id = getattr(tool_call, "id", None)
            call_id = getattr(tool_call, "call_id", None)
            if not isinstance(call_id, str) or not call_id.strip():
                embedded_call_id, _ = agent._split_responses_tool_id(raw_id)
                call_id = embedded_call_id
            if not isinstance(call_id, str) or not call_id.strip():
                if isinstance(raw_id, str) and raw_id.strip():
                    call_id = raw_id.strip()
                else:
                    call_id = f"call_{uuid.uuid4().hex[:12]}"
            call_id = call_id.strip()

            response_item_id = getattr(tool_call, "response_item_id", None)
            if not isinstance(response_item_id, str) or not response_item_id.strip():
                _, embedded_response_item_id = agent._split_responses_tool_id(raw_id)
                response_item_id = embedded_response_item_id

            response_item_id = agent._derive_responses_function_call_id(
                call_id,
                response_item_id if isinstance(response_item_id, str) else None,
            )

            tc_dict = {
                "id": call_id,
                "call_id": call_id,
                "response_item_id": response_item_id,
                "type": tool_call.type,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments
                },
            }
            extra = getattr(tool_call, "extra_content", None)
            if extra is not None:
                if hasattr(extra, "model_dump"):
                    extra = extra.model_dump()
                tc_dict["extra_content"] = extra
            tool_calls.append(tc_dict)
        msg["tool_calls"] = tool_calls

    return msg
