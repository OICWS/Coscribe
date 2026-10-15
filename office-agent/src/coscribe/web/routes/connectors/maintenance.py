"""Updating a connector: latest npm version, reconnect, bump."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from typing import Any

from fastapi import (
    APIRouter,
)

from ....tools import (
    validate_mcp_config,
)
from ...schemas import (
    MCPVersionBump,
)
from ...state import AppState
from ..shared import _read_mcp_servers_raw

# Plain name ("mcp-server-fetch") or scoped ("@playwright/mcp") npm package
# name -- deliberately doesn't allow anything npm view could misparse as a
# flag (e.g. a leading "-"), since `package` here comes straight from the
# browser.
_NPM_PACKAGE_NAME_RE = re.compile(r"^(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _connect_and_register_mcp_server_lg = state.connect_and_register_mcp_server_lg
    _disconnect_mcp_server_lg = state.disconnect_mcp_server_lg
    _refresh_all_sessions_extra_tools = state.refresh_all_sessions_extra_tools

    @router.get("/api/mcp/npm-latest-version")
    async def npm_latest_version(package: str) -> dict[str, Any]:
        if not _NPM_PACKAGE_NAME_RE.match(package):
            return {"error": "not a valid npm package name"}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [shutil.which("npm") or "npm", "view", package, "version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"error": str(exc)}
        if result.returncode != 0:
            return {"error": (result.stderr.strip() or "npm view failed")[-500:]}
        return {"package": package, "latest": result.stdout.strip()}

    @router.post("/api/mcp/servers/{name}/reconnect")
    async def reconnect_mcp_server(name: str) -> dict[str, Any]:
        """Retries a connect for an already-added server, unchanged --
        the gap add_mcp_server's own docstring names: once `isAdded` is
        true there was no way to replay a failed connect short of Remove
        + re-add, which also throws away the saved config. Same
        disconnect-then-reconnect shape as bump_mcp_server_version, just
        without touching the config at all first."""
        if settings.mcp_config_path is None or not settings.mcp_config_path.is_file():
            return {"error": "not found", "connected": False}
        raw = _read_mcp_servers_raw(settings.mcp_config_path)
        entry = raw["mcpServers"].get(name)
        if entry is None:
            return {"error": "not found", "connected": False}
        try:
            config = validate_mcp_config({"type": "mcp", "name": name, **entry})
        except ValueError as exc:
            return {"error": str(exc), "connected": False}
        await _disconnect_mcp_server_lg(name)
        connected, error = await _connect_and_register_mcp_server_lg(name, config)
        await _refresh_all_sessions_extra_tools()
        return {"connected": connected, "error": error}

    @router.post("/api/mcp/servers/{name}/bump-version")
    async def bump_mcp_server_version(name: str, payload: MCPVersionBump) -> dict[str, Any]:
        if settings.mcp_config_path is None or not settings.mcp_config_path.is_file():
            return {"error": "not found", "connected": False}
        raw = _read_mcp_servers_raw(settings.mcp_config_path)
        entry = raw["mcpServers"].get(name)
        if entry is None:
            return {"error": "not found", "connected": False}
        prefix = f"{payload.package}@"
        entry["args"] = [
            f"{payload.package}@{payload.version}" if arg.startswith(prefix) else arg
            for arg in entry.get("args", [])
        ]
        try:
            config = validate_mcp_config({"type": "mcp", "name": name, **entry})
        except ValueError as exc:
            return {"error": str(exc), "connected": False}
        raw["mcpServers"][name] = entry
        settings.mcp_config_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        await _disconnect_mcp_server_lg(name)
        connected, error = await _connect_and_register_mcp_server_lg(name, config)
        await _refresh_all_sessions_extra_tools()
        return {"connected": connected, "error": error}

    return router
