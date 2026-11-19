"""The connectors a workspace folder names in `.coscribe/mcp.json` (decision 0048), connected
for that folder's conversations once the person accepted the folder's settings.

Whoever can write the folder wrote these entries, so they connect with nothing of the person's:
no sign-in kept for a connector of the same name, no secret from Settings > Secrets, and the
proxy address without its user name and password.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..conversation import WorkspaceFolders
from ..runtime import SecretError, without_credentials
from ..tools import prepare_for_connect, validate_mcp_config

logger = logging.getLogger(__name__)

Connect = Callable[[str, Any], Awaitable[tuple[list[Any], Any, str | None]]]

# A server that failed (a first `uvx` download outlasting the connect timeout) is tried again
# on a later turn, waiting longer each time.
_RETRY_SECONDS = (30.0, 120.0, 600.0)
_CLOSE_WAIT_SECONDS = 15.0
_PROXY_VARIABLES = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")


@dataclass
class _Connected:
    key: str
    folder: Path
    servers: dict[str, Any]
    tools: list[Any] = field(default_factory=list)
    connections: list[Any] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)
    failures: int = 0
    retry_at: float = 0.0


def _refers_to_a_secret(entry: dict[str, Any]) -> bool:
    for name in ("env", "headers"):
        values = entry.get(name) or {}
        if not isinstance(values, dict):
            return True
        if any(not isinstance(v, str) or "{{secret:" in v for v in values.values()):
            return True
    return False


def _as_config(name: str, entry: dict[str, Any], folder: Path) -> dict[str, Any]:
    """Claude Code's `.mcp.json` entry in coscribe's own keys: `type` names the transport there
    and an HTTP server's address is `url`. A local server starts in the folder, as Claude Code
    starts a project's, and is handed the proxy without the person's credentials."""
    kind = entry.get("type", "stdio")
    config = {k: v for k, v in entry.items() if k not in ("type", "url")}
    if kind == "sse":
        raise ValueError("SSE servers aren't supported; use the server's HTTP address.")
    if kind == "http" and "url" in entry:
        config["server_url"] = entry["url"]
    elif kind not in ("stdio", "http"):
        raise ValueError(f"Unknown server type {kind!r}.")
    if "command" in config:
        config["cwd"] = str(folder / str(config.get("cwd", ".")))
        proxies = {
            name: without_credentials(value)
            for name in _PROXY_VARIABLES
            if (value := os.environ.get(name)) is not None
        }
        config["env"] = {**proxies, **(config.get("env") or {})}
    return {**config, "type": "mcp", "name": name}


class WorkspaceConnectors:
    def __init__(
        self,
        state_dir: Path,
        connect: Connect,
        refresh: Callable[[], Awaitable[None]],
        track: Callable[[asyncio.Task[None]], None],
    ) -> None:
        self._folders = WorkspaceFolders(state_dir)
        self._state_dir = state_dir
        self._connect = connect
        self._refresh = refresh
        self._track = track
        self._connected: dict[Path, _Connected] = {}
        # The key each folder is being connected for; a newer key makes an older run let go.
        self._wanted: dict[Path, str] = {}
        self._locks: dict[Path, asyncio.Lock] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def key(self, folder: Path) -> str:
        """What the folder's conversations should have: its accepted servers, or "" for none."""
        connected = self._connected.get(folder)
        return connected.key if connected else ""

    def tools(self, folder: Path) -> list[Any]:
        connected = self._connected.get(folder)
        return list(connected.tools) if connected else []

    def errors(self, folder: Path) -> dict[str, str]:
        connected = self._connected.get(folder)
        return dict(connected.errors) if connected else {}

    async def watch(self, folder: Path) -> None:
        """Bring `folder`'s connectors in line with what the person accepted. A connector no
        longer accepted is taken from its conversations before this returns; new ones connect
        in the background and reach the conversations when they are up."""
        try:
            servers = await asyncio.to_thread(self._folders.accepted_connectors, folder)
        except OSError:
            servers = {}
        key = json.dumps(servers, sort_keys=True, default=str) if servers else ""
        connected = self._connected.get(folder)
        if self._wanted.get(folder, connected.key if connected else "") == key:
            if connected and connected.errors and time.monotonic() >= connected.retry_at:
                self._start(self._retry(folder, connected))
            return
        self._wanted[folder] = key
        if connected is not None:
            del self._connected[folder]
            await self._refresh()
        self._start(self._sync(folder, servers, key, connected))

    def _start(self, work: Awaitable[None]) -> None:
        task = asyncio.ensure_future(work)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        self._track(task)

    async def _sync(
        self, folder: Path, servers: dict[str, Any], key: str, previous: _Connected | None
    ) -> None:
        async with self._locks.setdefault(folder, asyncio.Lock()):
            if previous is not None:
                await _close(previous)
            if self._wanted.get(folder) != key:
                return
            result = _Connected(key, folder, servers)
            kept: _Connected | None = None
            try:
                await self._connect_all(result, list(servers))
                if self._wanted.get(folder) != key:
                    return
                self._wanted.pop(folder, None)
                if servers:
                    self._connected[folder] = kept = result
            finally:
                if kept is None:
                    await asyncio.shield(_close(result))
            await self._refresh()

    async def _retry(self, folder: Path, connected: _Connected) -> None:
        connected.retry_at = float("inf")
        async with self._locks.setdefault(folder, asyncio.Lock()):
            if self._connected.get(folder) is not connected:
                return
            names = list(connected.errors)
            connected.errors.clear()
            before = len(connected.tools)
            await self._connect_all(connected, names)
            if self._connected.get(folder) is not connected:
                await asyncio.shield(_close(connected))
                return
            if len(connected.tools) != before:
                await self._refresh()

    async def _connect_all(self, result: _Connected, names: list[str]) -> None:
        errors = await asyncio.gather(
            *(self._connect_one(result, name, result.servers[name]) for name in names)
        )
        for name, error in zip(names, errors, strict=True):
            if error:
                result.errors[name] = error
        if result.errors:
            wait = _RETRY_SECONDS[min(result.failures, len(_RETRY_SECONDS) - 1)]
            result.failures += 1
            result.retry_at = time.monotonic() + wait

    async def _connect_one(self, result: _Connected, name: str, entry: Any) -> str | None:
        if not isinstance(entry, dict):
            return "Not a server entry."
        if _refers_to_a_secret(entry):
            return "A folder's connector can't use secrets from Settings."
        try:
            config = validate_mcp_config(_as_config(name, entry, result.folder))
            config = prepare_for_connect(config, self._state_dir)
        except (ValueError, RuntimeError, SecretError) as exc:
            return str(exc)
        tools, connection, error = await self._connect(name, config)
        if connection is None:
            return error or "Could not connect."
        if not tools:
            await asyncio.shield(connection.close())
            return "The server connected but offers no tools."
        result.connections.append(connection)
        result.tools.extend(tools)
        return None

    async def close(self) -> None:
        """Lets a connection still being made finish first: cancelled inside the MCP client, its
        server process would outlive the app."""
        self._wanted.clear()
        if self._tasks:
            await asyncio.wait(set(self._tasks), timeout=_CLOSE_WAIT_SECONDS)
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for connected in self._connected.values():
            await _close(connected)
        self._connected.clear()


async def _close(connected: _Connected) -> None:
    results = await asyncio.gather(
        *(connection.close() for connection in connected.connections), return_exceptions=True
    )
    connected.connections.clear()
    for result in results:
        if isinstance(result, BaseException):
            logger.warning("Closing a workspace connector failed: %s", result)
