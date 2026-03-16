"""Tool execution loop helpers extracted from run_agent.AIAgent (T2)."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import random
import time

from agent.display import KawaiiSpinner, build_tool_preview as _build_tool_preview, get_cute_tool_message as _get_cute_tool_message_impl, _detect_tool_failure
from openmork_arm_registry import get_arm_registry

logger = logging.getLogger(__name__)

_NEVER_PARALLEL_TOOLS = frozenset({"clarify"})
_MAX_TOOL_WORKERS = 8


def execute_tool_calls(agent, assistant_message, messages: list, effective_task_id: str, api_call_count: int = 0) -> None:
    tool_calls = assistant_message.tool_calls
    if (len(tool_calls) <= 1 or any(tc.function.name in _NEVER_PARALLEL_TOOLS for tc in tool_calls)):
        return execute_tool_calls_sequential(agent, assistant_message, messages, effective_task_id, api_call_count)
    return execute_tool_calls_concurrent(agent, assistant_message, messages, effective_task_id, api_call_count)


def invoke_tool(agent, function_name: str, function_args: dict, effective_task_id: str) -> str:
    if function_name == "todo":
        from tools.todo_tool import todo_tool as _todo_tool
        return _todo_tool(
            todos=function_args.get("todos"),
            merge=function_args.get("merge", False),
            store=agent._todo_store,
        )
    elif function_name == "session_search":
        if not agent._session_db:
            return json.dumps({"success": False, "error": "Session database not available."})
        from tools.session_search_tool import session_search as _session_search
        return _session_search(
            query=function_args.get("query", ""),
            role_filter=function_args.get("role_filter"),
            limit=function_args.get("limit", 3),
            db=agent._session_db,
            current_session_id=agent.session_id,
        )
    elif function_name == "memory":
        target = function_args.get("target", "memory")
        from tools.memory_tool import memory_tool as _memory_tool
        result = _memory_tool(
            action=function_args.get("action"),
            target=target,
            content=function_args.get("content"),
            old_text=function_args.get("old_text"),
            store=agent._memory_store,
        )
        if agent._honcho and target == "user" and function_args.get("action") == "add":
            agent._honcho_save_user_observation(function_args.get("content", ""))
        return result
    elif function_name == "clarify":
        from tools.clarify_tool import clarify_tool as _clarify_tool
        return _clarify_tool(
            question=function_args.get("question", ""),
            choices=function_args.get("choices"),
            callback=agent.clarify_callback,
        )
    elif function_name == "delegate_task":
        from tools.delegate_tool import delegate_task as _delegate_task
        return _delegate_task(
            goal=function_args.get("goal"),
            context=function_args.get("context"),
            toolsets=function_args.get("toolsets"),
            tasks=function_args.get("tasks"),
            max_iterations=function_args.get("max_iterations"),
            parent_agent=agent,
        )
    else:
        from model_tools import handle_function_call

        return handle_function_call(
            function_name, function_args, effective_task_id,
            enabled_tools=list(agent.valid_tool_names) if agent.valid_tool_names else None,
        )


def execute_tool_calls_concurrent(agent, assistant_message, messages: list, effective_task_id: str, api_call_count: int = 0) -> None:
    tool_calls = assistant_message.tool_calls
    num_tools = len(tool_calls)

    if agent._interrupt_requested:
        print(f"{agent.log_prefix}⚡ Interrupt: skipping {num_tools} tool call(s)")
        for tc in tool_calls:
            messages.append({
                "role": "tool",
                "content": f"[Tool execution cancelled — {tc.function.name} was skipped due to user interrupt]",
                "tool_call_id": tc.id,
            })
        return

    parsed_calls = []
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        if function_name == "memory":
            agent._turns_since_memory = 0
        elif function_name == "skill_manage":
            agent._iters_since_skill = 0

        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            function_args = {}
        if not isinstance(function_args, dict):
            function_args = {}

        if function_name in ("write_file", "patch") and agent._checkpoint_mgr.enabled:
            try:
                file_path = function_args.get("path", "")
                if file_path:
                    work_dir = agent._checkpoint_mgr.get_working_dir_for_path(file_path)
                    agent._checkpoint_mgr.ensure_checkpoint(work_dir, f"before {function_name}")
            except Exception as e:
                logger.warning("Checkpoint pre-save failed before %s: %s", function_name, e)

        parsed_calls.append((tool_call, function_name, function_args))

    tool_names_str = ", ".join(name for _, name, _ in parsed_calls)
    if not agent.quiet_mode:
        print(f"  ⚡ Concurrent: {num_tools} tool calls — {tool_names_str}")
        for i, (_, name, args) in enumerate(parsed_calls, 1):
            args_str = json.dumps(args, ensure_ascii=False)
            args_preview = args_str[:agent.log_prefix_chars] + "..." if len(args_str) > agent.log_prefix_chars else args_str
            print(f"  📞 Tool {i}: {name}({list(args.keys())}) - {args_preview}")

    for _, name, args in parsed_calls:
        if agent.tool_progress_callback:
            try:
                preview = _build_tool_preview(name, args)
                agent.tool_progress_callback(name, preview, args)
            except Exception as cb_err:
                logging.debug(f"Tool progress callback error: {cb_err}")

    results = [None] * num_tools

    def _run_tool(index, function_name, function_args):
        start = time.time()
        try:
            result = invoke_tool(agent, function_name, function_args, effective_task_id)
        except Exception as tool_error:
            result = f"Error executing tool '{function_name}': {tool_error}"
            logger.error("invoke_tool raised for %s: %s", function_name, tool_error, exc_info=True)
        duration = time.time() - start
        is_error, _ = _detect_tool_failure(function_name, result)
        results[index] = (function_name, function_args, result, duration, is_error)

    spinner = None
    if agent.quiet_mode:
        face = random.choice(KawaiiSpinner.KAWAII_WAITING)
        spinner = KawaiiSpinner(f"{face} ⚡ running {num_tools} tools concurrently", spinner_type='dots')
        spinner.start()

    try:
        max_workers = min(num_tools, _MAX_TOOL_WORKERS)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_run_tool, i, name, args) for i, (_, name, args) in enumerate(parsed_calls)]
            concurrent.futures.wait(futures)
    finally:
        if spinner:
            completed = sum(1 for r in results if r is not None)
            total_dur = sum(r[3] for r in results if r is not None)
            spinner.stop(f"⚡ {completed}/{num_tools} tools completed in {total_dur:.1f}s total")

    for i, (tc, name, args) in enumerate(parsed_calls):
        r = results[i]
        if r is None:
            function_result = f"Error executing tool '{name}': thread did not return a result"
            tool_duration = 0.0
        else:
            function_name, function_args, function_result, tool_duration, is_error = r
            if is_error:
                result_preview = function_result[:200] if len(function_result) > 200 else function_result
                logger.warning("Tool %s returned error (%.2fs): %s", function_name, tool_duration, result_preview)
            if agent.verbose_logging:
                result_preview = function_result[:200] if len(function_result) > 200 else function_result
                logging.debug(f"Tool {function_name} completed in {tool_duration:.2f}s")
                logging.debug(f"Tool result preview: {result_preview}...")

        if agent.quiet_mode:
            cute_msg = _get_cute_tool_message_impl(name, args, tool_duration, result=function_result)
            print(f"  {cute_msg}")
        elif not agent.quiet_mode:
            response_preview = function_result[:agent.log_prefix_chars] + "..." if len(function_result) > agent.log_prefix_chars else function_result
            print(f"  ✅ Tool {i+1} completed in {tool_duration:.2f}s - {response_preview}")

        MAX_TOOL_RESULT_CHARS = 100_000
        if len(function_result) > MAX_TOOL_RESULT_CHARS:
            original_len = len(function_result)
            function_result = (
                function_result[:MAX_TOOL_RESULT_CHARS]
                + f"\n\n[Truncated: tool response was {original_len:,} chars, "
                f"exceeding the {MAX_TOOL_RESULT_CHARS:,} char limit]"
            )

        messages.append({
            "role": "tool",
            "content": function_result,
            "tool_call_id": tc.id,
        })

    budget_warning = agent._get_budget_warning(api_call_count)
    if budget_warning and messages and messages[-1].get("role") == "tool":
        last_content = messages[-1]["content"]
        try:
            parsed = json.loads(last_content)
            if isinstance(parsed, dict):
                parsed["_budget_warning"] = budget_warning
                messages[-1]["content"] = json.dumps(parsed, ensure_ascii=False)
            else:
                messages[-1]["content"] = last_content + f"\n\n{budget_warning}"
        except (json.JSONDecodeError, TypeError):
            messages[-1]["content"] = last_content + f"\n\n{budget_warning}"
        if not agent.quiet_mode:
            remaining = agent.max_iterations - api_call_count
            tier = "⚠️  WARNING" if remaining <= agent.max_iterations * 0.1 else "💡 CAUTION"
            print(f"{agent.log_prefix}{tier}: {remaining} iterations remaining")


def execute_tool_calls_sequential(agent, assistant_message, messages: list, effective_task_id: str, api_call_count: int = 0) -> None:
    for i, tool_call in enumerate(assistant_message.tool_calls, 1):
        if agent._interrupt_requested:
            remaining_calls = assistant_message.tool_calls[i-1:]
            if remaining_calls:
                agent._vprint(f"{agent.log_prefix}⚡ Interrupt: skipping {len(remaining_calls)} tool call(s)", force=True)
            for skipped_tc in remaining_calls:
                skipped_name = skipped_tc.function.name
                messages.append({
                    "role": "tool",
                    "content": f"[Tool execution cancelled — {skipped_name} was skipped due to user interrupt]",
                    "tool_call_id": skipped_tc.id,
                })
            break

        function_name = tool_call.function.name
        if function_name == "memory":
            agent._turns_since_memory = 0
        elif function_name == "skill_manage":
            agent._iters_since_skill = 0

        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            function_args = {}
        if not isinstance(function_args, dict):
            function_args = {}

        if not agent.quiet_mode:
            args_str = json.dumps(function_args, ensure_ascii=False)
            args_preview = args_str[:agent.log_prefix_chars] + "..." if len(args_str) > agent.log_prefix_chars else args_str
            print(f"  📞 Tool {i}: {function_name}({list(function_args.keys())}) - {args_preview}")

        if agent.tool_progress_callback:
            try:
                preview = _build_tool_preview(function_name, function_args)
                agent.tool_progress_callback(function_name, preview, function_args)
            except Exception as cb_err:
                logging.debug(f"Tool progress callback error: {cb_err}")

        if function_name in ("write_file", "patch") and agent._checkpoint_mgr.enabled:
            try:
                file_path = function_args.get("path", "")
                if file_path:
                    work_dir = agent._checkpoint_mgr.get_working_dir_for_path(file_path)
                    agent._checkpoint_mgr.ensure_checkpoint(work_dir, f"before {function_name}")
            except Exception as e:
                logger.warning("Checkpoint pre-save failed before %s: %s", function_name, e)

        tool_start_time = time.time()

        if function_name == "delegate_task":
            from tools.delegate_tool import delegate_task as _delegate_task
            tasks_arg = function_args.get("tasks")
            if tasks_arg and isinstance(tasks_arg, list):
                spinner_label = f"🔀 delegating {len(tasks_arg)} tasks"
            else:
                goal_preview = (function_args.get("goal") or "")[:30]
                spinner_label = f"🔀 {goal_preview}" if goal_preview else "🔀 delegating"
            spinner = None
            if agent.quiet_mode:
                face = random.choice(KawaiiSpinner.KAWAII_WAITING)
                spinner = KawaiiSpinner(f"{face} {spinner_label}", spinner_type='dots')
                spinner.start()
            agent._delegate_spinner = spinner
            _delegate_result = None
            try:
                function_result = _delegate_task(
                    goal=function_args.get("goal"),
                    context=function_args.get("context"),
                    toolsets=function_args.get("toolsets"),
                    tasks=tasks_arg,
                    max_iterations=function_args.get("max_iterations"),
                    parent_agent=agent,
                )
                _delegate_result = function_result
            finally:
                agent._delegate_spinner = None
                tool_duration = time.time() - tool_start_time
                cute_msg = _get_cute_tool_message_impl('delegate_task', function_args, tool_duration, result=_delegate_result)
                if spinner:
                    spinner.stop(cute_msg)
                elif agent.quiet_mode:
                    agent._vprint(f"  {cute_msg}")
        elif agent.quiet_mode and agent._stream_callback is None:
            face = random.choice(KawaiiSpinner.KAWAII_WAITING)
            tool_emoji_map = {
                'web_search': '🔍', 'web_extract': '📄', 'web_crawl': '🕸️',
                'terminal': '💻', 'process': '⚙️',
                'read_file': '📖', 'write_file': '✍️', 'patch': '🔧', 'search_files': '🔎',
                'browser_navigate': '🌐', 'browser_snapshot': '📸',
                'browser_click': '👆', 'browser_type': '⌨️',
                'browser_scroll': '📜', 'browser_back': '◀️',
                'browser_press': '⌨️', 'browser_close': '🚪',
                'browser_get_images': '🖼️', 'browser_vision': '👁️',
                'image_generate': '🎨', 'text_to_speech': '🔊',
                'vision_analyze': '👁️', 'mixture_of_agents': '🧠',
                'skills_list': '📚', 'skill_view': '📚',
                'cronjob': '⏰',
                'send_message': '📨', 'todo': '📋', 'memory': '🧠', 'session_search': '🔍',
                'clarify': '❓', 'execute_code': '🐍', 'delegate_task': '🔀',
            }
            emoji = tool_emoji_map.get(function_name, '⚡')
            preview = _build_tool_preview(function_name, function_args) or function_name
            if len(preview) > 30:
                preview = preview[:27] + "..."
            spinner = KawaiiSpinner(f"{face} {emoji} {preview}", spinner_type='dots')
            spinner.start()
            _spinner_result = None
            try:
                function_result = invoke_tool(agent, function_name, function_args, effective_task_id)
                _spinner_result = function_result
            except Exception as tool_error:
                function_result = f"Error executing tool '{function_name}': {tool_error}"
                logger.error("handle_function_call raised for %s: %s", function_name, tool_error, exc_info=True)
            finally:
                tool_duration = time.time() - tool_start_time
                cute_msg = _get_cute_tool_message_impl(function_name, function_args, tool_duration, result=_spinner_result)
                spinner.stop(cute_msg)
        else:
            try:
                function_result = invoke_tool(agent, function_name, function_args, effective_task_id)
            except Exception as tool_error:
                function_result = f"Error executing tool '{function_name}': {tool_error}"
                logger.error("invoke_tool raised for %s: %s", function_name, tool_error, exc_info=True)
            tool_duration = time.time() - tool_start_time
            if agent.quiet_mode and function_name != "delegate_task":
                agent._vprint(f"  {_get_cute_tool_message_impl(function_name, function_args, tool_duration, result=function_result)}")

        result_preview = function_result[:200] if len(function_result) > 200 else function_result
        _is_error_result, _ = _detect_tool_failure(function_name, function_result)
        if _is_error_result:
            logger.warning("Tool %s returned error (%.2fs): %s", function_name, tool_duration, result_preview)

        arm_type = agent._arm_type_for_tool(function_name)
        if arm_type:
            get_arm_registry().record_call(arm_type, latency_ms=max(0.0, tool_duration) * 1000.0, error=_is_error_result)

        if agent.verbose_logging:
            logging.debug(f"Tool {function_name} completed in {tool_duration:.2f}s")
            logging.debug(f"Tool result preview: {result_preview}...")

        MAX_TOOL_RESULT_CHARS = 100_000
        if len(function_result) > MAX_TOOL_RESULT_CHARS:
            original_len = len(function_result)
            function_result = (
                function_result[:MAX_TOOL_RESULT_CHARS]
                + f"\n\n[Truncated: tool response was {original_len:,} chars, "
                f"exceeding the {MAX_TOOL_RESULT_CHARS:,} char limit]"
            )

        messages.append({
            "role": "tool",
            "content": function_result,
            "tool_call_id": tool_call.id,
        })

        if not agent.quiet_mode:
            response_preview = function_result[:agent.log_prefix_chars] + "..." if len(function_result) > agent.log_prefix_chars else function_result
            print(f"  ✅ Tool {i} completed in {tool_duration:.2f}s - {response_preview}")

        if agent._interrupt_requested and i < len(assistant_message.tool_calls):
            remaining = len(assistant_message.tool_calls) - i
            agent._vprint(f"{agent.log_prefix}⚡ Interrupt: skipping {remaining} remaining tool call(s)", force=True)
            for skipped_tc in assistant_message.tool_calls[i:]:
                skipped_name = skipped_tc.function.name
                messages.append({
                    "role": "tool",
                    "content": f"[Tool execution skipped — {skipped_name} was not started. User sent a new message]",
                    "tool_call_id": skipped_tc.id
                })
            break

        if agent.tool_delay > 0 and i < len(assistant_message.tool_calls):
            time.sleep(agent.tool_delay)

    budget_warning = agent._get_budget_warning(api_call_count)
    if budget_warning and messages and messages[-1].get("role") == "tool":
        last_content = messages[-1]["content"]
        try:
            parsed = json.loads(last_content)
            if isinstance(parsed, dict):
                parsed["_budget_warning"] = budget_warning
                messages[-1]["content"] = json.dumps(parsed, ensure_ascii=False)
            else:
                messages[-1]["content"] = last_content + f"\n\n{budget_warning}"
        except (json.JSONDecodeError, TypeError):
            messages[-1]["content"] = last_content + f"\n\n{budget_warning}"
        if not agent.quiet_mode:
            remaining = agent.max_iterations - api_call_count
            tier = "⚠️  WARNING" if remaining <= agent.max_iterations * 0.1 else "💡 CAUTION"
            print(f"{agent.log_prefix}{tier}: {remaining} iterations remaining")
