"""The connector catalog."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
)

from ...connector_catalog import MCP_CATALOG, SeenTools
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _connector_tools = state.connector_tools
    mcp_connections = state.mcp_connections

    @router.get("/api/mcp/catalog")
    async def get_mcp_catalog() -> list[dict[str, Any]]:
        """The catalog, each entry's tools being what the service reported
        when it was connected if that ever happened, else what the maker's
        documentation lists."""
        seen = SeenTools(settings.state_dir)
        for entry in MCP_CATALOG:
            name = entry["name"]
            if name in mcp_connections:
                seen.remember(name, [t["name"][len(name) + 1 :] for t in _connector_tools(name)])
        remembered = seen.load()
        result = []
        for entry in MCP_CATALOG:
            tools = remembered.get(entry["name"])
            if tools:
                result.append({**entry, "tools": tools, "tools_from": "service"})
            elif entry.get("tools"):
                result.append({**entry, "tools_from": "docs"})
            else:
                result.append(entry)
        return result

    return router
