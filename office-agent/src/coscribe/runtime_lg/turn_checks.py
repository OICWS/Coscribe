"""Two checks that keep a turn going until its work is done, without a person pushing it.

A model often ends a turn with tasks of its own plan still open, and the user has to say "you
didn't finish"; the plan check reads the plan when the model stops and sends it back once per
turn. A model that lost track also makes the same read again, and the repeat note on that call's
result says so, rather than blocking a call that may be right (the file may have changed, or an
earlier result may have been cleared from the context)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, after_model
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..runtime import get_tool_metadata
from .messages import is_plan_check, plan_check_message, starts_a_turn
from .tool_deferral import unwrap_use_tool_call

PLAN_CHECK = (
    "{tasks}\n\nBefore you end your turn: continue any of these you can do now. If one is "
    "done or no longer needed, update it. If you need something from the user, ask for it in "
    "your reply. Don't repeat what you already told the user."
)
_PLAN_TOOLS = frozenset({"task_create", "task_update"})
REPEAT_NOTE = (
    "\n\n[You already made this same call earlier in this turn. If nothing it reads has "
    "changed, use that result rather than calling again; if it didn't give you what you need, "
    "try another way.]"
)


def _this_turn(messages: Sequence[Any]) -> list[Any]:
    for index in range(len(messages) - 1, -1, -1):
        if starts_a_turn(messages[index]):
            return list(messages[index + 1 :])
    return list(messages)


def _worked_on_plan(turn: Sequence[Any]) -> bool:
    # Tasks left from work the user moved on from are not this turn's business.
    return any(
        call["name"] in _PLAN_TOOLS
        for message in turn
        for call in getattr(message, "tool_calls", None) or []
    )


def _plan_check(open_tasks: Callable[[], str]) -> AgentMiddleware:
    """When the model ends a turn that worked on its plan with tasks still open, send them back
    to it once in that turn."""

    @after_model(can_jump_to=["model"])
    def plan_check(state: Any, runtime: Any) -> dict[str, Any] | None:
        messages = state["messages"]
        last = messages[-1] if messages else None
        if not isinstance(last, AIMessage) or last.tool_calls:
            return None
        turn = _this_turn(messages)
        if any(is_plan_check(m) for m in turn) or not _worked_on_plan(turn):
            return None
        tasks = open_tasks()
        if not tasks:
            return None
        note = plan_check_message(PLAN_CHECK.format(tasks=tasks))
        return {"messages": [note], "jump_to": "model"}

    return plan_check


def _key(name: str, args: dict[str, Any]) -> tuple[str, str]:
    name, args = unwrap_use_tool_call(name, args)
    return name, json.dumps(args, sort_keys=True, default=str)


def repeats_earlier_call(call: dict[str, Any], messages: Sequence[Any], changers: set[str]) -> bool:
    """The same call with the same arguments was made earlier in this turn, and no call that
    changes things was made since."""
    wanted = _key(call["name"], call.get("args") or {})
    for message in reversed(_this_turn(messages)):
        for earlier in reversed(getattr(message, "tool_calls", None) or []):
            if earlier.get("id") == call.get("id"):
                continue
            key = _key(earlier["name"], earlier.get("args") or {})
            if key[0] in changers:
                return False
            if key == wanted:
                return True
    return False


# Reads whose result is the same until something changes it. A status check or a task list is
# asked again on purpose, so those are not watched.
_WATCHED_CATEGORIES = frozenset({"filesystem", "documents", "web"})


def repeat_note(tools: Sequence[Callable[..., Any] | BaseTool]) -> Callable[[Any, Any], Any]:
    """What adds the repeat note to a tool call's result. It runs inside the middleware that
    catches tool errors, which has the sync hook a sub-agent's own run needs as well as the
    async one."""
    watched: set[str] = set()
    changers: set[str] = set()
    for tool in tools:
        name = str(getattr(tool, "name", None) or getattr(tool, "__name__", ""))
        metadata = get_tool_metadata(cast(Callable[..., Any], tool))
        if metadata.risk_category != "READ" or metadata.category == "subagents":
            changers.add(name)
        elif metadata.category in _WATCHED_CATEGORIES:
            watched.add(name)

    def note(request: Any, result: Any) -> Any:
        call = request.tool_call
        name, _ = unwrap_use_tool_call(call["name"], call.get("args") or {})
        if (
            name not in watched
            or not isinstance(result, ToolMessage)
            or not isinstance(result.content, str)
            or not repeats_earlier_call(call, request.state["messages"], changers)
        ):
            return result
        return result.model_copy(update={"content": result.content + REPEAT_NOTE})

    return note


def plan_check(open_tasks: Callable[[], str] | None) -> list[AgentMiddleware]:
    return [] if open_tasks is None else [_plan_check(open_tasks)]
