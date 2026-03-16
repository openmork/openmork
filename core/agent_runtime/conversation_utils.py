"""Conversation/execution helpers extracted from ``run_agent.py``."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def max_tokens_param(base_url: str, value: int) -> Dict[str, int]:
    """Return provider-compatible max tokens kwarg for API requests."""
    is_direct_openai = (
        "api.openai.com" in (base_url or "").lower()
        and "openrouter" not in (base_url or "").lower()
    )
    if is_direct_openai:
        return {"max_completion_tokens": value}
    return {"max_tokens": value}


def has_content_after_think_block(content: str) -> bool:
    """Check whether content still has visible text after stripping think blocks."""
    if not content:
        return False
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    return bool(cleaned.strip())


def strip_think_blocks(content: str) -> str:
    """Remove <think>...</think> blocks, returning only visible text."""
    if not content:
        return ""
    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)


def looks_like_codex_intermediate_ack(
    user_message: str,
    assistant_content: str,
    messages: List[Dict[str, Any]],
) -> bool:
    """Detect planning/ack outputs that should continue instead of ending turn."""
    if any(isinstance(msg, dict) and msg.get("role") == "tool" for msg in messages):
        return False

    assistant_text = strip_think_blocks(assistant_content or "").strip().lower()
    if not assistant_text:
        return False
    if len(assistant_text) > 1200:
        return False

    has_future_ack = bool(
        re.search(r"\b(i['’]ll|i will|let me|i can do that|i can help with that)\b", assistant_text)
    )
    if not has_future_ack:
        return False

    action_markers = (
        "look into",
        "look at",
        "inspect",
        "scan",
        "check",
        "analyz",
        "review",
        "explore",
        "read",
        "open",
        "run",
        "test",
        "fix",
        "debug",
        "search",
        "find",
        "walkthrough",
        "report back",
        "summarize",
    )
    workspace_markers = (
        "directory",
        "current directory",
        "current dir",
        "cwd",
        "repo",
        "repository",
        "codebase",
        "project",
        "folder",
        "filesystem",
        "file tree",
        "files",
        "path",
    )

    user_text = (user_message or "").strip().lower()
    user_targets_workspace = (
        any(marker in user_text for marker in workspace_markers)
        or "~/" in user_text
        or "/" in user_text
    )
    assistant_mentions_action = any(marker in assistant_text for marker in action_markers)
    assistant_targets_workspace = any(marker in assistant_text for marker in workspace_markers)
    return (user_targets_workspace or assistant_targets_workspace) and assistant_mentions_action


def extract_reasoning_from_message(assistant_message: Any) -> Optional[str]:
    """Extract reasoning text from multiple provider-specific message formats."""
    reasoning_parts = []

    if hasattr(assistant_message, "reasoning") and assistant_message.reasoning:
        reasoning_parts.append(assistant_message.reasoning)

    if hasattr(assistant_message, "reasoning_content") and assistant_message.reasoning_content:
        if assistant_message.reasoning_content not in reasoning_parts:
            reasoning_parts.append(assistant_message.reasoning_content)

    if hasattr(assistant_message, "reasoning_details") and assistant_message.reasoning_details:
        for detail in assistant_message.reasoning_details:
            if isinstance(detail, dict):
                summary = detail.get("summary") or detail.get("content") or detail.get("text")
                if summary and summary not in reasoning_parts:
                    reasoning_parts.append(summary)

    if reasoning_parts:
        return "\n\n".join(reasoning_parts)
    return None
