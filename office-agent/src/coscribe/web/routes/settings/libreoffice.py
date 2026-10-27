"""Settings › Capabilities: the optional LibreOffice (decision 0026)."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

from ....tools import libreoffice_status
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    async def get_libreoffice() -> dict[str, Any]:
        # Asking a copy for its version starts it, which can take seconds.
        return dict(await asyncio.to_thread(libreoffice_status, state.settings.state_dir))

    router.add_api_route("/api/libreoffice", get_libreoffice, methods=["GET"])
    return router
