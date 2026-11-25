"""Checks that keep a turn going until its work is done, without a person pushing it.

A model often ends a turn with tasks of its own plan still open, or with a Word, Excel or
PowerPoint file it wrote that doesn't open, and the user has to say "you didn't finish" or "the
file is broken"; the turn-end check reads the plan and opens those files (delivery_check.py) when
the model stops, and sends what it finds back once per turn. A model that lost track also makes
the same read again, and the repeat note on that call's result says so, rather than blocking a
call that may be right (the file may have changed, or an earlier result may have been cleared
from the context)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

from langchain.agents.middleware import AgentMiddleware, after_model, hook_config
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from ..runtime import get_tool_metadata
from .delivery_check import broken_office_files
from .messages import is_plan_check, plan_check_message, starts_a_turn
from .tool_deferral import unwrap_use_tool_call

PLAN_CHECK = (
    "{tasks}\n\nBefore you end your turn: continue any of these you can do now. If one is "
    "done or no longer needed, update it. If you need something from the user, ask for it in "
    "your reply. Don't repeat what you already told the user."
)
DELIVERY_CHECK = (
    "These Office files you wrote this turn don't open, so the user can't use them:\n{files}\n\n"
    "Before you end your turn, fix or rebuild them, or tell the user what went wrong."
)
_PLAN_TOOLS = frozenset({"task_create", "task_update"})
_ASK_TOOL = "ask_user_question"
_ANSWER_TOOL = "answer_question_card"
_SHOWN = "The questions are on a card"
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


def _asked(turn: Sequence[Any]) -> bool:
    return any(isinstance(m, ToolMessage) and m.name == _ASK_TOOL for m in turn)


def _end_notes(
    turn: Sequence[Any],
    open_tasks: Callable[[], str] | None,
    writers: set[str],
    resolve_file: Callable[[str], Path] | None,
    *,
    asked: bool = False,
) -> list[str]:
    if any(is_plan_check(m) for m in turn):
        return []
    notes = []
    # After a question the model may stop on purpose: what's left waits on the answer
    # (decision 0060).
    if open_tasks is not None and not asked and _worked_on_plan(turn):
        tasks = open_tasks()
        if tasks:
            notes.append(PLAN_CHECK.format(tasks=tasks))
    if resolve_file is not None:
        broken = broken_office_files(turn, writers, resolve_file)
        if broken:
            notes.append(DELIVERY_CHECK.format(files="\n".join(broken)))
    return notes


def _turn_end(
    open_tasks: Callable[[], str] | None,
    writers: set[str],
    resolve_file: Callable[[str], Path] | None,
) -> AgentMiddleware:
    """When the model ends a turn that worked on its plan with tasks still open, or that wrote
    an Office file which doesn't open, send that back to it once in that turn."""

    @after_model(can_jump_to=["model"])
    def turn_end_check(state: Any, runtime: Any) -> dict[str, Any] | None:
        messages = state["messages"]
        last = messages[-1] if messages else None
        if not isinstance(last, AIMessage) or last.tool_calls:
            return None
        turn = _this_turn(messages)
        notes = _end_notes(turn, open_tasks, writers, resolve_file, asked=_asked(turn))
        if not notes:
            return None
        return {"messages": [plan_check_message("\n\n".join(notes))], "jump_to": "model"}

    return turn_end_check


_ENDED_TURN = "ends_turn"


class _EndsTurnMiddleware(AgentMiddleware):
    """A step whose calls were all to tools that end the turn (an emoji on the user's message)
    ends it there, with no model call to follow; the turn-end checks still get their say first.
    A call that failed goes back to the model like any other, so it sees the error. Such a
    call's result is marked by `repeat_note` (`_ENDED_TURN` in its response_metadata, which no
    provider is sent), so the page can also tell a turn that ended this way from a model that
    went quiet."""

    def __init__(
        self,
        open_tasks: Callable[[], str] | None,
        writers: set[str],
        resolve_file: Callable[[str], Path] | None,
    ) -> None:
        super().__init__()
        self._checks = (open_tasks, writers, resolve_file)

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        messages = state["messages"]
        results: list[Any] = []
        for message in reversed(messages):
            if not isinstance(message, ToolMessage):
                break
            results.append(message)
        if not results or not all(m.response_metadata.get(_ENDED_TURN) for m in results):
            return None
        notes = _end_notes(_this_turn(messages), *self._checks)
        if notes:
            return {"messages": [plan_check_message("\n\n".join(notes))]}
        return {"jump_to": "end"}

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.before_model(state, runtime)


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


def _card_size(messages: Sequence[Any]) -> int:
    """How many questions the latest card the person was shown asks; 0 when there was none."""
    failed: set[str] = set()
    shown: set[str] = set()
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and message.status == "error":
            failed.add(message.tool_call_id)
        elif isinstance(message, ToolMessage) and str(message.content).startswith(_SHOWN):
            shown.add(message.tool_call_id)
        for call in reversed(getattr(message, "tool_calls", None) or []):
            name, args = unwrap_use_tool_call(call["name"], call.get("args") or {})
            if name == _ASK_TOOL and call.get("id") not in failed:
                questions = args.get("questions")
                # A conversation from before cards stopped waiting has the answer as the result.
                if call.get("id") not in shown or not isinstance(questions, list):
                    return 0
                return len(questions)
    return 0


def _check_card_answer(args: dict[str, Any], messages: Sequence[Any]) -> None:
    """answer_question_card can't see the card, so the count of answers is checked here: a short
    list would close the card with questions the person never answered."""
    size = _card_size(messages)
    answers = args.get("answers")
    given = len(answers) if isinstance(answers, list) else 0
    if size == 0:
        raise ValueError("No question card was shown in this conversation.")
    if given != size:
        raise ValueError(
            f"The card asks {size} question(s) and this gives {given} answer(s), in the card's "
            "order. It closes only once every question is answered: ask about the rest in your "
            "reply instead."
        )


def repeat_note(tools: Sequence[Callable[..., Any] | BaseTool]) -> Callable[[Any, Any], Any]:
    """What adds the repeat note to a tool call's result, and marks the result of one that ends
    the turn (`_EndsTurnMiddleware`). It runs inside the middleware that
    catches tool errors, which has the sync hook a sub-agent's own run needs as well as the
    async one."""
    watched: set[str] = set()
    changers: set[str] = set()
    ending: set[str] = set()
    for tool in tools:
        name = str(getattr(tool, "name", None) or getattr(tool, "__name__", ""))
        metadata = get_tool_metadata(cast(Callable[..., Any], tool))
        if metadata.ends_turn:
            ending.add(name)
        if metadata.risk_category != "READ" or metadata.category == "subagents":
            changers.add(name)
        elif metadata.category in _WATCHED_CATEGORIES:
            watched.add(name)

    def note(request: Any, result: Any) -> Any:
        call = request.tool_call
        name, args = unwrap_use_tool_call(call["name"], call.get("args") or {})
        if name == _ANSWER_TOOL and isinstance(result, ToolMessage) and result.status != "error":
            _check_card_answer(args, request.state["messages"])
        if name in ending and isinstance(result, ToolMessage) and result.status != "error":
            marks = {**result.response_metadata, _ENDED_TURN: True}
            return result.model_copy(update={"response_metadata": marks})
        if (
            name not in watched
            or not isinstance(result, ToolMessage)
            or not isinstance(result.content, str)
            or not repeats_earlier_call(call, request.state["messages"], changers)
        ):
            return result
        return result.model_copy(update={"content": result.content + REPEAT_NOTE})

    return note


def turn_end(
    open_tasks: Callable[[], str] | None,
    tools: Sequence[Callable[..., Any] | BaseTool],
    resolve_file: Callable[[str], Path] | None,
) -> list[AgentMiddleware]:
    metadata = {
        str(getattr(t, "name", None) or getattr(t, "__name__", "")): get_tool_metadata(
            cast(Callable[..., Any], t)
        )
        for t in tools
    }
    writers = {name for name, m in metadata.items() if m.risk_category == "WRITE_LOCAL"}
    ending = {name for name, m in metadata.items() if m.ends_turn}
    middleware: list[AgentMiddleware] = []
    if open_tasks is not None or resolve_file is not None:
        middleware.append(_turn_end(open_tasks, writers, resolve_file))
    if ending:
        middleware.append(_EndsTurnMiddleware(open_tasks, writers, resolve_file))
    return middleware
