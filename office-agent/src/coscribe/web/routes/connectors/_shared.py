"""Helpers several connector route modules use."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import (
    Request,
)

# Deferred import for the same reason as runtime_lg.mcp (see the comment
# above MCP_STARTUP_TIMEOUT_SECONDS).
from ....runtime_lg.mcp_oauth import (
    APP_REDIRECT_URI,
    SIGN_IN_TIMEOUT_SECONDS,
    CallbackPortBusy,
    NeedsSignIn,
)
from ...connector_catalog import MCP_CATALOG
from ...state import AppState


def make_begin_oauth_sign_in(
    state: AppState,
) -> Callable[[str, Any, Request], Awaitable[dict[str, Any]]]:
    mcp_oauth = state.mcp_oauth
    app_callback = state.app_callback
    _disconnect_mcp_server_lg = state.disconnect_mcp_server_lg
    _connect_and_register_mcp_server_lg = state.connect_and_register_mcp_server_lg
    _refresh_all_sessions_extra_tools = state.refresh_all_sessions_extra_tools
    sign_in_tasks = state.sign_in_tasks

    async def _begin_oauth_sign_in(name: str, config: Any, request: Request) -> dict[str, Any]:
        """Starts signing in to a connector and returns once there is
        something to show: connected, failed, or the sign-in page's address
        (already opened in the user's browser). The connection keeps
        waiting for the redirect in the background; the Connectors page
        sees the result through GET /api/mcp/servers."""
        app_group = config.get("oauth_app")
        setup: dict[str, Any] = next(
            (
                e["setup"]
                for e in MCP_CATALOG
                if app_group and e.get("setup", {}).get("group") == app_group
            ),
            {},
        )
        if app_group:
            if mcp_oauth.app(app_group) is None:
                return {"connected": False, "error": "Set up the app for this connector first."}
            try:
                await app_callback.start()
            except CallbackPortBusy as exc:
                return {"connected": False, "error": str(exc)}
            redirect_uri = APP_REDIRECT_URI
        else:
            redirect_uri = f"{str(request.base_url).rstrip('/')}/api/mcp/oauth/callback"
        try:
            flow = await mcp_oauth.begin(
                name,
                redirect_uri,
                app=app_group,
                scope=" ".join(setup["scopes"]) if setup.get("scopes") else None,
                auth_params=setup.get("auth_params"),
            )
        except NeedsSignIn as exc:
            await app_callback.stop()
            return {"connected": False, "error": str(exc)}
        await _disconnect_mcp_server_lg(name)

        async def connect() -> None:
            connected, error = False, None
            try:
                connected, error = await _connect_and_register_mcp_server_lg(
                    name, config, SIGN_IN_TIMEOUT_SECONDS + 30
                )
                await _refresh_all_sessions_extra_tools()
            except Exception as exc:  # noqa: BLE001 -- shown to the user, not swallowed
                error = str(exc) or type(exc).__name__
            mcp_oauth.finish(flow, None if connected else error or "Couldn't sign in.")
            if app_callback.running and not any(
                mcp_oauth.pending(n) for n in list(mcp_oauth._active)
            ):
                await app_callback.stop()

        task = asyncio.create_task(connect())
        sign_in_tasks.add(task)
        task.add_done_callback(sign_in_tasks.discard)
        try:
            await asyncio.wait_for(flow.url_ready.wait(), timeout=30)
        except TimeoutError:
            return {"connected": False, "error": "The server didn't offer a sign-in page."}
        if flow.finished.is_set():
            return {"connected": flow.error is None, "error": flow.error}
        return {"connected": False, "signin": {"url": flow.url}}

    return _begin_oauth_sign_in
