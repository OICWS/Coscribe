"""The OAuth redirect and signing in again."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Request,
)
from fastapi.responses import HTMLResponse

from ....tools import (
    validate_mcp_config,
)
from ...state import AppState
from ..shared import _read_mcp_servers_raw
from ._shared import make_begin_oauth_sign_in


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _oauth_callback_response = state.oauth_callback_response
    _begin_oauth_sign_in = make_begin_oauth_sign_in(state)

    @router.get("/api/mcp/oauth/callback", response_class=HTMLResponse)
    async def mcp_oauth_callback(
        state: str = "", code: str | None = None, error: str | None = None
    ) -> HTMLResponse:
        status, body = _oauth_callback_response(state, code, error)
        return HTMLResponse(body, status_code=status)

    @router.post("/api/mcp/servers/{name}/signin")
    async def sign_in_mcp_server(name: str, request: Request) -> dict[str, Any]:
        """Signs in again to an OAuth connector whose saved sign-in no longer
        works."""
        if settings.mcp_config_path is None or not settings.mcp_config_path.is_file():
            return {"error": "not found", "connected": False}
        entry = _read_mcp_servers_raw(settings.mcp_config_path)["mcpServers"].get(name)
        if entry is None or entry.get("auth") != "oauth":
            return {"error": "not found", "connected": False}
        config = validate_mcp_config({"type": "mcp", "name": name, **entry})
        return await _begin_oauth_sign_in(name, config, request)

    return router
