"""Clearing old tool results from what the model is sent, before a conversation needs compacting.

Most of a long office conversation is tool output the model has already used: a document read
in full, a search's hits, a script's printout. LangChain's `ClearToolUsesEdit` replaces older
results with a placeholder, but it moves its boundary on every call (or, with
`clear_at_least`, clears one fixed amount and then nothing more), and a provider's prompt cache
is lost from the first message that changes. Here the boundary moves in steps of `STEP` tool
results, so the cached prefix is lost about once every `STEP` tool calls rather than on each.
Only the request is edited: the history keeps every result, so compaction and the transcript
still read them whole.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import ContextEditingMiddleware
from langchain_core.messages import AnyMessage, ToolMessage

KEEP = 6
STEP = 8
PLACEHOLDER = (
    "[This earlier tool result was cleared to save context. Call the tool again if you need it.]"
)
# Results the model can't get back by calling again, or that steer the rest of the work: the
# plan, the user's answers, a skill's instructions, a sub-agent's report, a found tool's schema.
KEPT_TOOLS = frozenset(
    {
        "task_create",
        "task_list",
        "task_update",
        "ask_user_question",
        "remember",
        "load_skill",
        "read_skill_file",
        "spawn_agent",
        "spawn_agent_background",
        "review_work",
        "search_tools",
    }
)


class ClearOldToolResults:
    """A `ContextEdit` (LangChain's protocol): edits the request's copy of the messages."""

    def __init__(self, trigger_tokens: int) -> None:
        self.trigger_tokens = trigger_tokens

    def apply(self, messages: list[AnyMessage], *, count_tokens: Any) -> None:
        if count_tokens(messages) <= self.trigger_tokens:
            return
        clearable = [
            i
            for i, m in enumerate(messages)
            if isinstance(m, ToolMessage) and m.name not in KEPT_TOOLS
        ]
        count = (max(0, len(clearable) - KEEP) // STEP) * STEP
        for i in clearable[:count]:
            messages[i] = messages[i].model_copy(update={"content": PLACEHOLDER, "artifact": None})


def clear_old_tool_results_middleware(trigger_tokens: int) -> ContextEditingMiddleware:
    return ContextEditingMiddleware(edits=[ClearOldToolResults(trigger_tokens)])
