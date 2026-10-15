"""The memory file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
)

from ....tools import load_memory
from ...schemas import (
    MemoryUpdate,
)
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings

    @router.get("/api/memory")
    async def get_memory() -> dict[str, Any]:
        # Settings.memory_path can change mid-session (a folder change
        # re-resolves it, see set_folders) -- reading settings.memory_path
        # fresh here rather than caching it at app-build time keeps this
        # endpoint honest about whichever file the *next* new thread would
        # actually load, same "read fresh, no stale cache" posture
        # get_config's own dotenv_values(".env") call takes.
        return {"content": load_memory(settings.memory_path)}

    @router.post("/api/memory")
    async def update_memory(payload: MemoryUpdate) -> dict[str, Any]:
        # Directly overwrites the file -- the Settings panel's own text
        # box is the whole editing surface here, so a full
        # overwrite is the correct semantics for "save what's in the box."
        # Same "next new thread only" gap this project already accepts
        # for provider/skill config changes (see this module's own
        # docstring) -- an already-open thread keeps whatever memory
        # content it started with until its process restarts or a fresh
        # thread opens.
        path = Path(settings.memory_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload.content, encoding="utf-8")
        return {"status": "ok"}

    return router
