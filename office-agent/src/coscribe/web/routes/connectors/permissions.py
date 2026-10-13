"""Per-tool permissions of a connector."""

from __future__ import annotations

from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse

# Deferred import for the same reason as runtime_lg.mcp (see the comment
# above MCP_STARTUP_TIMEOUT_SECONDS).
from ....tools.connector_permissions import (
    POLICIES,
    ConnectorPermissions,
)
from ...schemas import (
    ConnectorPermissionsUpdate,
)
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _connector_tools = state.connector_tools
    _refresh_all_sessions_extra_tools = state.refresh_all_sessions_extra_tools

    @router.put("/api/mcp/servers/{name}/permissions")
    async def set_connector_permissions(
        name: str, payload: ConnectorPermissionsUpdate
    ) -> JSONResponse:
        known = {t["name"] for t in _connector_tools(name)}
        unknown = sorted(set(payload.tools) - known)
        if unknown:
            return JSONResponse(
                {"error": f"{name!r} has no tool {', '.join(unknown)}"}, status_code=404
            )
        try:
            tools = ConnectorPermissions(settings.state_dir).update(name, payload.tools)
        except ValueError:
            return JSONResponse(
                {"error": f"a policy must be one of {', '.join(POLICIES)}"}, status_code=422
            )
        await _refresh_all_sessions_extra_tools()
        return JSONResponse({"tools": tools})

    return router
