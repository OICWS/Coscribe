"""Every tool call in a history needs a result after it, or the provider
rejects the whole request with a 400; and what a turn the user stopped leaves in it."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from .messages import extract_text, plan_check_message, starts_a_turn
from .tool_deferral import unwrap_use_tool_call

ORPHANED_TOOL_CALL_NOTE = "Stopped before this tool finished -- it produced no result."


def answer_every_tool_call(messages: list[Any]) -> tuple[list[Any], bool]:
    """`messages` with a placeholder result for each tool call that never got
    one, and whether any was added. The placeholder sits directly after its
    AIMessage -- after the results that did arrive (a partly finished
    parallel batch), before whatever follows -- since a history already
    corrupted has a newer message after the orphan."""
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    rebuilt: list[Any] = []
    patched = False
    index = 0
    while index < len(messages):
        message = messages[index]
        rebuilt.append(message)
        index += 1
        if not isinstance(message, AIMessage) or not message.tool_calls:
            continue
        while index < len(messages) and isinstance(messages[index], ToolMessage):
            rebuilt.append(messages[index])
            index += 1
        for call in message.tool_calls:
            if call["id"] not in answered:
                patched = True
                rebuilt.append(
                    ToolMessage(
                        content=ORPHANED_TOOL_CALL_NOTE,
                        tool_call_id=call["id"],
                        name=call["name"],
                    )
                )
    return rebuilt, patched


STOPPED_MARKER = "[stopped]"
# What a question still open at a stop is answered with (ChatSessionLG.request_stop).
_STOPPED_BEFORE_ANSWER = "(Stopped by user before answering.)"


def stopped_turn_messages(
    messages: Sequence[Any], text: str, running: Sequence[str]
) -> list[BaseMessage]:
    """What a turn the user stopped adds after `messages`: the reply it had written so far,
    ending in the stop marker, and a note the next turn reads first, since without it the
    model takes up the stopped work again or repeats finished steps. `running` names the
    background work the stop left going."""
    added: list[BaseMessage] = []
    last = messages[-1] if messages else None
    said = text.strip()
    if said and not (isinstance(last, AIMessage) and extract_text(last.content).strip() == said):
        added.append(AIMessage(content=f"{said}\n\n{STOPPED_MARKER}"))
    start = max((i for i, m in enumerate(messages) if starts_a_turn(m)), default=-1)
    names = {}
    for message in messages[start + 1 :]:
        for call in getattr(message, "tool_calls", None) or []:
            names[call["id"]] = unwrap_use_tool_call(call["name"], call.get("args") or {})[0]
    results = [m for m in messages[start + 1 :] if isinstance(m, ToolMessage)]
    cut = [
        names.get(m.tool_call_id, m.name or "a tool")
        for m in results
        if m.content == ORPHANED_TOOL_CALL_NOTE
    ]
    note = "[The user pressed Stop and ended your previous turn there."
    if cut:
        note += f" These calls were cut off and did not finish: {', '.join(cut)}."
    if any(m.content == _STOPPED_BEFORE_ANSWER for m in results):
        note += (
            " Your question was left unanswered: don't ask it again first thing; answer their"
            " next message, and ask again only if you still need to."
        )
    note += (
        " Steps that finished keep their results, so don't redo them, and don't take the "
        "stopped work up again unless the user asks: answer their next message."
    )
    if running:
        note += f" Still running in the background, not stopped: {'; '.join(running)}."
    added.append(plan_check_message(note + "]"))
    return added
