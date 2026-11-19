"""The connectors a workspace folder names in `.coscribe/mcp.json` (decision 0048), connected
for that folder's conversations once the person accepted the folder's settings.

Whoever can write the folder wrote these entries, so they connect with nothing of the person's:
no sign-in kept for a connector of the same name, and no secret from Settings > Secrets.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..conversation import WorkspaceFolders
from ..runtime import SecretError
from ..tools import prepare_for_connect, validate_mcp_config

logger = logging.getLogger(__name__)

Connect = Callable[[str, Any], Awaitable[tuple[list[Any], Any, str | None]]]


@dataclass
class _Connected:
    key: str
    tools: list[Any] = field(default_factory=list)
    connections: list[Any] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def _refers_to_a_secret(entry: dict[str, Any]) -> bool:
    for name in ("env", "headers"):
        values = entry.get(name) or {}
        if not isinstance(values, dict):
            return True
        if any(not isinstance(v, str) or "{{secret:" in v for v in values.values()):
            return True
    return False


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
        servers = self._folders.accepted_connectors(folder)
        key = json.dumps(servers, sort_keys=True, default=str) if servers else ""
        connected = self._connected.get(folder)
        if self._wanted.get(folder, connected.key if connected else "") == key:
            return
        self._wanted[folder] = key
        if connected is not None:
            del self._connected[folder]
            await self._refresh()
        task = asyncio.create_task(self._sync(folder, servers, key, connected))
        self._track(task)

    async def _sync(
        self, folder: Path, servers: dict[str, Any], key: str, previous: _Connected | None
    ) -> None:
        async with self._locks.setdefault(folder, asyncio.Lock()):
            if previous is not None:
                await _close(previous)
            if self._wanted.get(folder) != key:
                return
            result = _Connected(key)
            for name, entry in servers.items():
                error = await self._connect_one(result, name, entry)
                if error:
                    result.errors[name] = error
            if self._wanted.get(folder) != key:
                await _close(result)
                return
            self._wanted.pop(folder, None)
            if not servers:
                return
            self._connected[folder] = result
            await self._refresh()

    async def _connect_one(self, result: _Connected, name: str, entry: Any) -> str | None:
        if not isinstance(entry, dict):
            return "Not a server entry."
        if _refers_to_a_secret(entry):
            return "A folder's connector can't use secrets from Settings."
        try:
            config = validate_mcp_config({**entry, "type": "mcp", "name": name})
            config = prepare_for_connect(config, self._state_dir)
        except (ValueError, RuntimeError, SecretError) as exc:
            return str(exc)
        tools, connection, error = await self._connect(name, config)
        if connection is None:
            return error or "Could not connect."
        if not tools:
            await connection.close()
            return "The server connected but offers no tools."
        result.tools.extend(tools)
        result.connections.append(connection)
        return None

    async def close(self) -> None:
        self._wanted.clear()
        for connected in self._connected.values():
            await _close(connected)
        self._connected.clear()


async def _close(connected: _Connected) -> None:
    results = await asyncio.gather(
        *(connection.close() for connection in connected.connections), return_exceptions=True
    )
    for result in results:
        if isinstance(result, BaseException):
            logger.warning("Closing a workspace connector failed: %s", result)
