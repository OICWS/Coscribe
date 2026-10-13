"""The hosted and local MCP connectors a running app holds: their tools, their live
connections, and the rebuild of open conversations when either changes. Reads settings
and the state dir, nothing from FastAPI, so it runs without building the app."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from ..config import Settings
from ..runtime import SecretError, get_tool_metadata
from ..tools import (
    ConnectorPermissions,
    apply_connector_permissions,
    connector_of,
    is_read_only,
    name_of,
    prepare_for_connect,
    validate_mcp_config,
)
from ..workflows import tool_description
from .routes.shared import _read_mcp_servers_raw


class _OpenSession(Protocol):
    async def refresh_extra_tools(self, tools: list[Any]) -> None: ...


class ConnectorManager:
    def __init__(
        self,
        settings: Settings,
        sessions: Mapping[str, _OpenSession],
        auth_for: Callable[..., Any],
    ) -> None:
        self._settings = settings
        self._sessions = sessions
        self._auth_for = auth_for
        # Plain mutable attributes rather than module globals, since the app may be
        # built more than once (e.g. once per test). `tools` does NOT have the
        # guarantee of being filled before the first session opens, deliberately:
        # see the app's lifespan MCP-connect comment for why a session opened very
        # early may briefly see fewer tools than a slow-to-connect MCP server will
        # eventually provide.
        self.tools: list[Any] = []
        # {server_name: McpServerConnection} for every currently-connected MCP
        # server -- each owns a persistent session/subprocess (see runtime_lg/
        # mcp.py's module docstring for why persistent, not the previous
        # per-tool-call default) that must be explicitly close()d when this
        # server disconnects/reconnects or the app shuts down, or its
        # subprocess (and, for Playwright, its browser) leaks past that point.
        self.connections: dict[str, Any] = {}
        self.sign_in_tasks: set[asyncio.Task[None]] = set()
        self._reconnecting: set[str] = set()

    def session_extra_tools(self) -> list[Any]:
        """The connector tools conversations get, under the permissions set
        in Settings > Connectors."""
        return apply_connector_permissions(
            self.tools, ConnectorPermissions(self._settings.state_dir).load()
        )

    def connector_tools(self, name: str) -> list[dict[str, Any]]:
        permissions = ConnectorPermissions(self._settings.state_dir).load().get(name, {})
        prefix = f"{name}_"
        result = []
        for tool in self.tools:
            if connector_of(tool) != name:
                continue
            full_name = name_of(tool)
            bare = full_name[len(prefix) :] if full_name.startswith(prefix) else full_name
            title = (getattr(tool, "metadata", None) or {}).get("title") or (
                bare.replace("-", " ").replace("_", " ").strip().capitalize()
            )
            result.append(
                {
                    "name": full_name,
                    "title": title,
                    "description": tool_description(tool).split(". ")[0],
                    "read_only": is_read_only(tool),
                    "policy": permissions.get(full_name, "ask"),
                }
            )
        return result

    async def disconnect_mcp_server_lg(self, name: str) -> None:
        """Strips `name`'s tools from `tools` so the *next* new
        session doesn't get them; already-open ChatSessionLG instances only
        stop seeing them once their caller also calls
        refresh_all_sessions_extra_tools() below (every current caller
        does, right after this). Async: also closes and forgets `name`'s
        McpServerConnection, if any -- unlike before the persistent-session
        fix (runtime_lg/mcp.py), there is now a real subprocess to actually
        tear down here, not just a tool list to filter."""
        self.tools = [
            t for t in self.tools if get_tool_metadata(t).category != f"mcp:{name}"
        ]
        connection = self.connections.pop(name, None)
        if connection is not None:
            await connection.close()

    def reconnect_stale_connector(self, name: str) -> None:
        """A connector call hung or hit a dead session: connect it afresh in
        the background, once at a time per connector."""
        if name in self._reconnecting:
            return
        self._reconnecting.add(name)

        async def reconnect() -> None:
            try:
                mcp_config_path = self._settings.mcp_config_path
                if mcp_config_path is None or not mcp_config_path.is_file():
                    return
                entry = _read_mcp_servers_raw(mcp_config_path)["mcpServers"].get(name)
                if entry is None:
                    return
                config = validate_mcp_config({"type": "mcp", "name": name, **entry})
                await self.disconnect_mcp_server_lg(name)
                await self.connect_and_register_mcp_server_lg(name, config)
                await self.refresh_all_sessions_extra_tools()
            except Exception:  # noqa: BLE001 -- the Connectors page shows it as not connected
                logging.getLogger(__name__).warning(
                    "Reconnecting connector %r failed", name, exc_info=True
                )
            finally:
                self._reconnecting.discard(name)

        task = asyncio.create_task(reconnect())
        self.sign_in_tasks.add(task)
        task.add_done_callback(self.sign_in_tasks.discard)

    async def connect_and_register_mcp_server_lg(
        self, name: str, config: Any, connect_timeout: float | None = None
    ) -> tuple[bool, str | None]:
        """Connects one MCP server and registers its tools into
        `tools`. Returns (connected, error) -- error is a
        human-readable failure reason from connect_one_mcp_server_lg, or
        None on success. connect_one_mcp_server_lg's only positive-connect
        signal is a non-empty tool list, same imprecision as treating a
        real server that happens to expose zero tools as "didn't connect";
        accepted here since real MCP servers always expose at least one
        tool in practice."""
        # Deferred import: runtime_lg.mcp drags in langchain_mcp_adapters and the mcp
        # SDK, ~250-360 ms of startup for a user with no MCP servers.
        from ..runtime_lg import connect_one_mcp_server_lg

        try:
            config = prepare_for_connect(config, self._settings.state_dir)
        except (SecretError, RuntimeError) as exc:
            return False, str(exc)
        extra = {} if connect_timeout is None else {"connect_timeout": connect_timeout}
        new_tools, connection, error = await connect_one_mcp_server_lg(
            name, config, self._auth_for, on_stale=self.reconnect_stale_connector, **extra
        )
        if connection is None:
            return False, error
        if not new_tools:
            # Connected, but a connector with no tools is no use, and its
            # session would otherwise stay open with nothing to close it.
            await connection.close()
            return False, "The server connected but offers no tools."
        self.tools.extend(new_tools)
        self.connections[name] = connection
        return True, None

    async def refresh_all_sessions_extra_tools(self) -> None:
        """Add/remove/bump_mcp_server only ever update `tools`, which the
        app's get_session only reads when constructing a *brand-new*
        ChatSessionLG -- a connector enabled mid-conversation would never show
        up in that same, already-open thread, only in threads started
        afterwards. Called once at the end of each of the three
        connector-mutating endpoints (not from inside
        disconnect_mcp_server_lg/connect_and_register_mcp_server_lg
        themselves, since add/bump call both back to back and would
        otherwise rebuild every open session's graph twice for one
        request). Best-effort per session -- ChatSessionLG.refresh_extra_
        tools already logs-and-keeps-previous-tools on its own failure, so
        one broken session's rebuild can't block the others from picking
        up the change."""
        tools = self.session_extra_tools()
        for session in self._sessions.values():
            await session.refresh_extra_tools(tools)
