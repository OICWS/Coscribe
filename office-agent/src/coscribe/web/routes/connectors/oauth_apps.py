"""OAuth app credentials for services that need a registered app."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse

# Deferred import for the same reason as runtime_lg.mcp (see the comment
# above MCP_STARTUP_TIMEOUT_SECONDS).
from ....runtime_lg.mcp_oauth import (
    APP_REDIRECT_URI,
)
from ...connector_catalog import MCP_CATALOG
from ...schemas import (
    OAuthAppCredentials,
    OAuthAppImport,
)
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    mcp_oauth = state.mcp_oauth

    @router.get("/api/mcp/oauth-apps")
    async def get_mcp_oauth_apps() -> dict[str, Any]:
        return {"saved": mcp_oauth.app_groups(), "redirect_uri": APP_REDIRECT_URI}

    @router.put("/api/mcp/oauth-apps/{group}")
    async def put_mcp_oauth_app(group: str, payload: OAuthAppCredentials) -> JSONResponse:
        client_id = payload.client_id.strip()
        secret = (payload.client_secret or "").strip() or None
        if not client_id or any(ch.isspace() for ch in client_id):
            return JSONResponse(
                {"error": "The Client ID is empty or has spaces in it."}, status_code=400
            )
        needs_secret = any(
            e.get("setup", {}).get("group") == group and e["setup"].get("needs_secret")
            for e in MCP_CATALOG
        )
        if needs_secret and secret is None:
            return JSONResponse(
                {"error": "This service needs the Client secret too."}, status_code=400
            )
        if secret is not None and any(ch.isspace() for ch in secret):
            return JSONResponse({"error": "The Client secret has spaces in it."}, status_code=400)
        mcp_oauth.set_app(group, client_id, secret)
        return JSONResponse({"saved": group})

    @router.delete("/api/mcp/oauth-apps/{group}")
    async def delete_mcp_oauth_app(group: str) -> dict[str, Any]:
        mcp_oauth.forget_app(group)
        return {"removed": group}

    @router.get("/api/mcp/oauth-apps/{group}/export")
    async def export_mcp_oauth_app(group: str) -> JSONResponse:
        credentials = mcp_oauth.app(group)
        if credentials is None:
            return JSONResponse({"error": "Nothing saved for this service."}, status_code=404)
        return JSONResponse(
            {
                "apps": {
                    group: {"client_id": credentials[0], "client_secret": credentials[1]},
                }
            }
        )

    @router.post("/api/mcp/oauth-apps/import")
    async def import_mcp_oauth_apps(payload: OAuthAppImport) -> JSONResponse:
        for group, credentials in payload.apps.items():
            if not credentials.client_id.strip():
                return JSONResponse({"error": f"{group}: the Client ID is empty."}, status_code=400)
        for group, credentials in payload.apps.items():
            mcp_oauth.set_app(group, credentials.client_id.strip(), credentials.client_secret)
        return JSONResponse({"imported": sorted(payload.apps)})

    return router
