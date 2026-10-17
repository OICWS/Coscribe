"""Secrets: values are write-only."""

from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse

from ....runtime import (
    KeychainUnavailable,
    SecretError,
    SecretStore,
    keychain_available,
    resolve_secret,
)
from ....tools import secret_names_used
from ...state import AppState
from ..shared import _read_mcp_servers_raw


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings

    # -- Secrets: values are write-only; nothing here ever returns one.

    def _connectors_using_secret(name: str) -> list[str]:
        if settings.mcp_config_path is None or not settings.mcp_config_path.is_file():
            return []
        servers = _read_mcp_servers_raw(settings.mcp_config_path)["mcpServers"]
        return sorted(
            server for server, entry in servers.items() if name in _secret_names_in_entry(entry)
        )

    def _secret_names_in_entry(entry: dict[str, Any]) -> set[str]:
        # Stored values may be keychain references, so read them back first.
        resolved: dict[str, Any] = {}
        for field in ("env", "headers"):
            values = entry.get(field) or {}
            resolved[field] = {k: _stored_text(v) for k, v in values.items()}
        return secret_names_used(resolved)

    def _stored_text(value: Any) -> str:
        # An unreadable value could be the one that names the secret, so the
        # caller treats it as in use rather than as nothing.
        return resolve_secret(value) or ""

    @router.get("/api/secrets")
    async def list_secrets() -> dict[str, Any]:
        return {
            "keychain": keychain_available(),
            "secrets": SecretStore(settings.state_dir).entries(),
        }

    @router.put("/api/secrets/{name}")
    async def put_secret(name: str, payload: dict[str, Any]) -> Any:
        try:
            return SecretStore(settings.state_dir).save(
                name, payload.get("value"), payload.get("hosts")
            )
        except KeychainUnavailable as exc:
            return JSONResponse(
                {"error": str(exc), "code": "keychain_unavailable"}, status_code=503
            )
        except SecretError as exc:
            return JSONResponse({"error": str(exc)}, status_code=422)

    @router.delete("/api/secrets/{name}")
    async def delete_secret_endpoint(name: str) -> Any:
        try:
            using = _connectors_using_secret(name)
        except RuntimeError as exc:
            return JSONResponse(
                {
                    "error": "A connector's saved settings can't be read from the keychain, so "
                    f"it can't be checked whether {name} is in use: {exc}"
                },
                status_code=503,
            )
        if using:
            return JSONResponse(
                {
                    "error": f"{name} is used by the connector {', '.join(using)}. "
                    "Change that connector first.",
                    "connectors": using,
                },
                status_code=409,
            )
        if not SecretStore(settings.state_dir).delete(name):
            return JSONResponse({"error": f"There is no secret named {name}."}, status_code=404)
        return {"deleted": name}

    return router
