"""The design-system library (decision 0020)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ....tools import DesignSystemError, DesignSystemStore
from ...state import AppState

# A kept SVG may hold script; opened at its own address it must not run in the app's origin.
_ASSET_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}
# Read at most a little past the limit, so an oversized upload is refused without holding it all.
_READ_LIMIT = 2 * 1024 * 1024 + 1


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

    async def duplicate_design_system(system_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """A copy with everything the original has, its pictures included."""
        try:
            return found(store.duplicate(system_id, str(payload.get("name", ""))))
        except DesignSystemError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    router.add_api_route(
        "/api/design-systems/{system_id}/duplicate", duplicate_design_system, methods=["POST"]
    )
    _asset_routes(router, store, found)

    @router.delete("/api/design-systems/{system_id}")
    async def delete_design_system(system_id: str) -> dict[str, str]:
        if not store.delete(system_id):
            raise HTTPException(status_code=404, detail="No such design system")
        return {"status": "ok"}

    return router


def _asset_routes(
    router: APIRouter,
    store: DesignSystemStore,
    found: Callable[[dict[str, Any] | None], dict[str, Any]],
) -> None:
    """A system's pictures: added from a file, renamed or noted, deleted, and drawn."""

    @router.post("/api/design-systems/{system_id}/assets")
    async def add_asset(system_id: str, file: UploadFile) -> dict[str, Any]:
        data = await file.read(_READ_LIMIT)
        try:
            return found(store.add_asset(system_id, data, file.filename or "Picture"))
        except DesignSystemError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.put("/api/design-systems/{system_id}/assets/{asset_id}")
    async def update_asset(
        system_id: str, asset_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            changed = store.update_asset(system_id, asset_id, payload)
        except DesignSystemError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if changed is None:
            raise HTTPException(status_code=404, detail="No such picture")
        return changed

    @router.delete("/api/design-systems/{system_id}/assets/{asset_id}")
    async def delete_asset(system_id: str, asset_id: str) -> dict[str, str]:
        if not store.delete_asset(system_id, asset_id):
            raise HTTPException(status_code=404, detail="No such picture")
        return {"status": "ok"}

    @router.get("/api/design-systems/{system_id}/assets/{asset_id}")
    async def asset_file(system_id: str, asset_id: str) -> FileResponse:
        kept = store.asset_file(system_id, asset_id)
        if kept is None:
            raise HTTPException(status_code=404, detail="No such picture")
        path, media = kept
        return FileResponse(path, media_type=media, headers=_ASSET_HEADERS)
