"""Configured connector servers: list, add and remove."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from dotenv import set_key
from fastapi import (
    APIRouter,
    Request,
)

from ....runtime import (
    delete_secret,
    harden_file_permissions,
    store_secret,
)
from ....runtime.secret_store import (
    SecretError,
    placeholders_in,
)
from ....tools.connector_permissions import (
    ConnectorPermissions,
)
from ....tools.mcp import (
    load_mcp_server_configs,
    validate_mcp_config,
    with_secrets,
)
from ...schemas import (
    MCPServerUpdate,
)
from ...state import AppState
from ..shared import _mask, _read_mcp_servers_raw
from ._shared import make_begin_oauth_sign_in


def _mask_value(value: str) -> str:
    """A connector value for display. One that refers to a secret is shown
    as written, placeholder and all, with any other text of it hidden (short
    pieces such as "Bearer " stay readable): the value itself is never in it."""
    if not placeholders_in(value):
        return _mask(value)
    parts = re.split(r"(\{\{secret:[A-Za-z_][A-Za-z0-9_]{0,63}\}\})", value)
    return "".join(
        part if placeholders_in(part) or len(part) <= 7 else "*" * len(part) for part in parts
    )


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _connector_tools = state.connector_tools
    mcp_connections = state.mcp_connections
    _connect_and_register_mcp_server_lg = state.connect_and_register_mcp_server_lg
    _disconnect_mcp_server_lg = state.disconnect_mcp_server_lg
    _refresh_all_sessions_extra_tools = state.refresh_all_sessions_extra_tools
    mcp_oauth = state.mcp_oauth
    _begin_oauth_sign_in = make_begin_oauth_sign_in(state)

    @router.get("/api/mcp/servers")
    async def get_mcp_servers() -> dict[str, Any]:
        if settings.mcp_config_path is None or not settings.mcp_config_path.is_file():
            return {}
        result: dict[str, Any] = {}
        for name, config in load_mcp_server_configs(
            settings.mcp_config_path, settings.state_dir, fill_secrets=False
        ).items():
            # `connected` reads the same live mcp_connections registry
            # every actual tool call goes through (see its own comment
            # above) -- a real signal, not derived from the static config
            # this loop is otherwise reading. Configured but not currently
            # connected covers both "never successfully connected" and
            # "connected once, then the subprocess/session died" -- this
            # endpoint doesn't distinguish those, same as the Connectors
            # tab never has (add/bump already surface a real error message
            # at the point of failure; this is just current live state).
            connected = name in mcp_connections
            try:
                with_secrets(config, settings.state_dir)
                secret_error = None
            except (SecretError, RuntimeError) as exc:
                secret_error = str(exc)
            if "server_url" in config:
                # Remote (streamable_http) entry -- a hand-configured
                # Custom-tab remote-server form. Bearer/auth header values
                # masked the same way env values are below -- never echoed
                # back to the browser in full.
                result[name] = {
                    "server_url": config["server_url"],
                    "masked_headers": {
                        k: _mask_value(v) for k, v in (config.get("headers") or {}).items()
                    },
                    "connected": connected,
                    "secret_error": secret_error,
                    "tools": _connector_tools(name),
                }
                if config.get("auth") == "oauth":
                    waiting = mcp_oauth.pending(name)
                    result[name]["auth"] = "oauth"
                    result[name]["signin"] = (
                        {"url": waiting.url} if waiting is not None and waiting.url else None
                    )
                    result[name]["signin_error"] = mcp_oauth.last_error(name)
            else:
                result[name] = {
                    "command": config.get("command"),
                    "args": config.get("args", []),
                    "masked_env": {k: _mask_value(v) for k, v in (config.get("env") or {}).items()},
                    "connected": connected,
                    "secret_error": secret_error,
                    "tools": _connector_tools(name),
                }
        return result

    @router.post("/api/mcp/servers")
    async def add_mcp_server(payload: MCPServerUpdate, request: Request) -> dict[str, Any]:
        if payload.server_url:
            entry: dict[str, Any] = {"server_url": payload.server_url}
            if payload.headers:
                entry["headers"] = payload.headers
            if payload.auth:
                entry["auth"] = payload.auth
                if payload.oauth_app:
                    entry["oauth_app"] = payload.oauth_app
        else:
            entry = {"command": payload.command, "args": payload.args}
            if payload.env:
                entry["env"] = payload.env
        try:
            config = validate_mcp_config({"type": "mcp", "name": payload.name, **entry})
        except ValueError as exc:
            return {"rejected": {payload.name: str(exc)}, "connected": False}

        try:
            with_secrets(config, settings.state_dir)
        except (SecretError, RuntimeError) as exc:
            return {"rejected": {payload.name: str(exc)}, "connected": False}

        # .resolve() -- see add_provider's identical fallback for why a
        # bare relative path here is a real, cwd-dependent bug.
        path = settings.mcp_config_path or Path("./mcp.json").resolve()
        raw = _read_mcp_servers_raw(path)
        # `config` above (used to actually connect, just below) keeps the
        # real env/headers values; only what's persisted to disk gets
        # routed through store_secret per value.
        stored_entry = dict(entry)
        if payload.env:
            stored_entry["env"] = {
                key: store_secret(f"mcp:{payload.name}:env:{key}", value)
                for key, value in payload.env.items()
            }
        if payload.headers:
            stored_entry["headers"] = {
                key: store_secret(f"mcp:{payload.name}:headers:{key}", value)
                for key, value in payload.headers.items()
            }
        raw["mcpServers"][payload.name] = stored_entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        harden_file_permissions(path)
        if settings.mcp_config_path is None:
            settings.mcp_config_path = path
            set_key(".env", "COSCRIBE_MCP_CONFIG_PATH", str(path))

        if config.get("auth") == "oauth":
            return {"rejected": {}, **await _begin_oauth_sign_in(payload.name, config, request)}
        await _disconnect_mcp_server_lg(payload.name)
        connected, error = await _connect_and_register_mcp_server_lg(payload.name, config)
        await _refresh_all_sessions_extra_tools()
        return {"rejected": {}, "connected": connected, "error": error}

    @router.delete("/api/mcp/servers/{name}")
    async def remove_mcp_server(name: str) -> dict[str, Any]:
        await _disconnect_mcp_server_lg(name)
        if settings.mcp_config_path is not None and settings.mcp_config_path.is_file():
            raw = _read_mcp_servers_raw(settings.mcp_config_path)
            removed = raw["mcpServers"].pop(name, None)
            if removed is not None:
                for value in (removed.get("env") or {}).values():
                    delete_secret(value)
                for value in (removed.get("headers") or {}).values():
                    delete_secret(value)
            settings.mcp_config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
            harden_file_permissions(settings.mcp_config_path)
        ConnectorPermissions(settings.state_dir).forget(name)
        mcp_oauth.forget(name)
        await _refresh_all_sessions_extra_tools()
        return {}

    return router
