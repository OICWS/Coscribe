"""Stopping an agent at a token budget (decision 0043), counted from its history like the model-call
limit, so a pause for an approval doesn't start the count again. A message the caller adds to let
the agent go on starts a new budget of the same size."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, HumanMessage

TOKEN_LIMIT_PREFIX = "Token budget used"


def tokens_used(messages: Sequence[Any]) -> int:
    """The new tokens the model replies in `messages` cost, as the provider reported them: what
    it served from its cache is billed far lower, and every call of a long agent re-reads it."""
    used = 0
    for message in messages:
        if isinstance(message, AIMessage) and message.usage_metadata:
            usage = message.usage_metadata
            cached = (usage.get("input_token_details") or {}).get("cache_read", 0) or 0
            used += int(usage["total_tokens"] or 0) - int(cached)
    return used


def since_go_on(messages: Sequence[Any], go_on: str) -> Sequence[Any]:
    """The messages after the last `go_on` the caller added; all of them before it adds one."""
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, HumanMessage) and message.content == go_on:
            return messages[index + 1 :]
    return messages


class TokenLimitMiddleware(AgentMiddleware):
    """Ends the agent before a model call once it has cost `limit` tokens since the last `go_on`
    message. The caller decides whether it goes on: by adding that message, it does."""

    def __init__(self, limit: int, go_on: str) -> None:
        super().__init__()
        self.limit = limit
        self.go_on = go_on

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        used = tokens_used(since_go_on(state["messages"], self.go_on))
        if used < self.limit:
            return None
        message = f"{TOKEN_LIMIT_PREFIX} ({used}/{self.limit})"
        return {"jump_to": "end", "messages": [AIMessage(content=message)]}

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.before_model(state, runtime)
