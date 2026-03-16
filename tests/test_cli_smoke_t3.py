from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _import_cli_module():
    stubs = {
        "dotenv": MagicMock(),
        "fire": MagicMock(),
        "run_agent": SimpleNamespace(AIAgent=object),
        "model_tools": SimpleNamespace(get_tool_definitions=lambda: [], get_toolset_for_tool=lambda _t: None),
        "tools": MagicMock(),
        "tools.terminal_tool": SimpleNamespace(
            cleanup_all_environments=lambda: None,
            set_sudo_password_callback=lambda _cb: None,
            set_approval_callback=lambda _cb: None,
        ),
        "tools.skills_tool": SimpleNamespace(set_secret_capture_callback=lambda _cb: None),
        "tools.browser_tool": SimpleNamespace(_emergency_cleanup_all_sessions=lambda: None),
        "openmork_cli.callbacks": SimpleNamespace(prompt_for_secret=lambda *_a, **_k: None),
        "prompt_toolkit": MagicMock(),
        "prompt_toolkit.history": MagicMock(),
        "prompt_toolkit.styles": MagicMock(),
        "prompt_toolkit.patch_stdout": MagicMock(),
        "prompt_toolkit.application": MagicMock(),
        "prompt_toolkit.layout": MagicMock(),
        "prompt_toolkit.layout.processors": MagicMock(),
        "prompt_toolkit.filters": MagicMock(),
        "prompt_toolkit.layout.dimension": MagicMock(),
        "prompt_toolkit.layout.menus": MagicMock(),
        "prompt_toolkit.widgets": MagicMock(),
        "prompt_toolkit.key_binding": MagicMock(),
        "prompt_toolkit.completion": MagicMock(),
        "prompt_toolkit.formatted_text": MagicMock(),
    }
    with patch.dict(sys.modules, stubs):
        import cli as cli_mod

        return importlib.reload(cli_mod)


class _DummyCLI:
    def __init__(self):
        self.called = []
        self.session_id = "session-xyz"
        self.console = type("C", (), {"print": lambda self, *_a, **_k: None})()
        self.agent = type("A", (), {"quiet_mode": False, "run_conversation": lambda self, _q: {"final_response": "ok"}})()
        self.tool_progress_mode = None

    def show_banner(self): self.called.append("show_banner")
    def show_tools(self): self.called.append("show_tools")
    def show_toolsets(self): self.called.append("show_toolsets")
    def _init_agent(self): self.called.append("init_agent"); return True
    def chat(self, _query): self.called.append("chat")
    def _print_exit_summary(self): self.called.append("print_exit_summary")
    def run(self): self.called.append("run")


def test_resolve_toolsets_string_and_default(monkeypatch):
    cli_mod = _import_cli_module()
    monkeypatch.setattr(cli_mod, "CLI_CONFIG", {"platform_toolsets": {"cli": ["a", "b"]}})
    assert cli_mod._resolve_toolsets_input("web,terminal") == ["web", "terminal"]
    assert cli_mod._resolve_toolsets_input(None) == ["a", "b"]


def test_dispatch_list_tools_exits():
    cli_mod = _import_cli_module()
    cli = _DummyCLI()
    with pytest.raises(SystemExit):
        cli_mod._dispatch_cli_mode(cli=cli, query=None, quiet=False, list_tools=True, list_toolsets=False)
    assert cli.called == ["show_banner", "show_tools"]


def test_dispatch_query_quiet(capsys):
    cli_mod = _import_cli_module()
    cli = _DummyCLI()
    cli_mod._dispatch_cli_mode(cli=cli, query="hola", quiet=True, list_tools=False, list_toolsets=False)
    out = capsys.readouterr().out
    assert "session_id: session-xyz" in out
    assert "init_agent" in cli.called


def test_dispatch_interactive_run():
    cli_mod = _import_cli_module()
    cli = _DummyCLI()
    cli_mod._dispatch_cli_mode(cli=cli, query=None, quiet=False, list_tools=False, list_toolsets=False)
    assert cli.called == ["run"]
