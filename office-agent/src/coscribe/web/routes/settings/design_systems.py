"""The design-system library (decision 0020)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ....tools import DesignSystemError, DesignSystemStore
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    store = DesignSystemStore(state.settings.state_dir)

    def found(system: dict[str, Any] | None) -> dict[str, Any]:
        if system is None:
            raise HTTPException(status_code=404, detail="No such design system")
        return system

    @router.get("/api/design-systems")
    async def list_design_systems() -> list[dict[str, Any]]:
        return store.list_systems()

    @router.post("/api/design-systems")
    async def create_design_system(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return store.create(str(payload.get("name", "")))
        except DesignSystemError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/api/design-systems/{system_id}")
    async def get_design_system(system_id: str) -> dict[str, Any]:
        return found(store.get(system_id))

    @router.put("/api/design-systems/{system_id}")
    async def update_design_system(system_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return found(store.update(system_id, payload))
        except DesignSystemError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/api/design-systems/{system_id}")
    async def delete_design_system(system_id: str) -> dict[str, str]:
        if not store.delete(system_id):
            raise HTTPException(status_code=404, detail="No such design system")
        return {"status": "ok"}

    return router
