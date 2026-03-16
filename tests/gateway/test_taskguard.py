from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from gateway.config import Platform
from gateway.run import GatewayRunner
from gateway.taskguard import ReportingTaskGuard


class _RecorderGuard:
    def __init__(self):
        self.calls = []
        self.manual = set()

    def start(self, task_id, ttl_min=None):
        self.calls.append(("start", task_id))

    def progress(self, task_id, note=None):
        self.calls.append(("progress", task_id, note))

    def done(self, task_id):
        self.calls.append(("done", task_id))

    def set_manual(self, task_id, enabled):
        if enabled:
            self.manual.add(task_id)
        else:
            self.manual.discard(task_id)

    def is_manual_enabled(self, task_id):
        return task_id in self.manual

    def status(self, task_id):
        return {
            "task_id": task_id,
            "manual_enabled": task_id in self.manual,
            "task": {"status": "running", "ttl_min": 12},
        }


def _make_runner_with_taskguard(taskguard):
    runner = GatewayRunner.__new__(GatewayRunner)
    runner.adapters = {}
    runner._taskguard = taskguard
    runner._provider_routing = {}
    runner._reasoning_config = {}
    runner._ephemeral_system_prompt = ""
    runner._prefill_messages = []
    runner._session_db = None
    runner._fallback_model = None
    runner._running_agents = {}
    runner.hooks = SimpleNamespace(loaded_hooks=False, emit=lambda *_args, **_kwargs: asyncio.sleep(0))
    runner.session_store = SimpleNamespace(_entries={})
    runner._load_reasoning_config = lambda: {}
    return runner


@pytest.mark.asyncio
async def test_taskguard_auto_start_progress_done_for_long_tool(monkeypatch):
    guard = _RecorderGuard()
    runner = _make_runner_with_taskguard(guard)

    monkeypatch.setattr("gateway.run._resolve_runtime_agent_kwargs", lambda: {"api_key": "k"})

    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.tool_cb = kwargs.get("tool_progress_callback")
            self.session_id = kwargs.get("session_id")
            self.context_compressor = SimpleNamespace(last_prompt_tokens=0)
            self.model = kwargs.get("model")
            self.tools = []

        def run_conversation(self, _message, conversation_history=None, task_id=None):
            self.tool_cb("terminal", "run pytest", {"command": "pytest -q", "timeout": 300})
            return {
                "final_response": "ok",
                "messages": [{"role": "assistant", "content": "ok"}],
                "api_calls": 1,
            }

    monkeypatch.setitem(sys.modules, "run_agent", SimpleNamespace(AIAgent=FakeAgent))

    src = SimpleNamespace(platform=Platform.TELEGRAM, chat_id="c1", thread_id=None, value="telegram")
    await runner._run_agent(
        message="haz esto",
        context_prompt="",
        history=[],
        source=src,
        session_id="sess-1",
        session_key="sk-1",
    )

    events = [c[0] for c in guard.calls]
    assert "start" in events
    assert "progress" in events
    assert events[-1] == "done"


@pytest.mark.asyncio
async def test_taskguard_manual_commands_on_off_status():
    guard = _RecorderGuard()
    runner = _make_runner_with_taskguard(guard)

    event = SimpleNamespace(get_command_args=lambda: "on demo-task")
    out = await runner._handle_taskguard_command(event)
    assert "ON" in out

    event = SimpleNamespace(get_command_args=lambda: "status demo-task")
    out = await runner._handle_taskguard_command(event)
    assert "manual: on" in out

    event = SimpleNamespace(get_command_args=lambda: "off demo-task")
    out = await runner._handle_taskguard_command(event)
    assert "OFF" in out


def test_taskguard_cooldown_prevents_repeated_alerts(tmp_path, monkeypatch):
    state = tmp_path / "guard.json"
    tg = ReportingTaskGuard(state_path=state, default_ttl_min=1, default_cooldown_min=30)

    now = 10_000
    monkeypatch.setattr("gateway.taskguard.time.time", lambda: now)
    tg.start("task-a", ttl_min=1)

    monkeypatch.setattr("gateway.taskguard.time.time", lambda: now + 61)
    first = tg.check(ttl_min=1, cooldown_min=30)
    assert first and first[0]["task_id"] == "task-a"

    monkeypatch.setattr("gateway.taskguard.time.time", lambda: now + 120)
    second = tg.check(ttl_min=1, cooldown_min=30)
    assert second == []
