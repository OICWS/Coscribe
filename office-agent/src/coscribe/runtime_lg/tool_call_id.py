"""Binds the id of the tool call that is running, for the tool to find.

A tool function cannot take its call id as an argument (its schema is fixed, decision 0001),
yet the chat's "Run in background" button names a running tool row by that id. The binding
reaches a tool on a worker thread because the executor copies the context into the thread.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware

from ..tools import tool_call_id


class ToolCallIdMiddleware(AgentMiddleware):
    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        with tool_call_id(request.tool_call["id"]):
            return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        with tool_call_id(request.tool_call["id"]):
            return await handler(request)
