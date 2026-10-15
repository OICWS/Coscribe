"""The configured hook commands a conversation runs around its tool calls and its own
lifecycle. Only PreToolUse can veto; every other event is reported and a failure is only
logged, so the action it describes is never held up by a broken hook."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..runtime import run_hook

logger = logging.getLogger(__name__)


async def run_pre_tool_use(
    hooks_config: dict[str, list[str]], name: str, args: dict[str, Any]
) -> str | None:
    """The denial reason if a PreToolUse hook vetoes this call, None if all pass.
    `run_hook` blocks on a subprocess, so it runs off the event loop."""
    if not hooks_config["PreToolUse"]:
        return None
    payload = {
        "event": "PreToolUse",
        "tool_name": name,
        "arguments": args,
        "agent_name": "coordinator",
    }
    for command in hooks_config["PreToolUse"]:
        result = await asyncio.to_thread(run_hook, command, payload)
        if not result.allowed:
            return result.reason
    return None


async def run_post_tool_use(
    hooks_config: dict[str, list[str]], name: str, args: dict[str, Any], result: Any
) -> None:
    if not hooks_config["PostToolUse"]:
        return
    payload = {
        "event": "PostToolUse",
        "tool_name": name,
        "arguments": args,
        "agent_name": "coordinator",
        "result": result,
    }
    for command in hooks_config["PostToolUse"]:
        outcome = await asyncio.to_thread(run_hook, command, payload)
        if not outcome.allowed:
            logger.warning("PostToolUse hook failed: %s", outcome.reason)


async def run_observational(
    hooks_config: dict[str, list[str]], event: str, payload: dict[str, Any]
) -> None:
    for command in hooks_config.get(event, []):
        outcome = await asyncio.to_thread(run_hook, command, payload)
        if not outcome.allowed:
            logger.warning("%s hook failed: %s", event, outcome.reason)
