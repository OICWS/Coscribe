"""The Artifacts page: the decks, documents and spreadsheets coscribe made, kept apart from
the conversations that made them."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from ...conversation import describe_artifact
from ...tools import WorkspaceScope, foreign_slide_svg, slide_svg
from ..artifact_adoption import ArtifactAdoption
from ..state import AppState
from .slides import _SVG_HEADERS

_LISTED = ("path", "name", "kind", "modified_at", "excerpt")


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    adoption = ArtifactAdoption(
        settings, state.thread_files, state.sessions, state.checkpointer_holder
    )

    def described(artifact: str) -> tuple[dict[str, Any], dict[str, Any], WorkspaceScope] | None:
        """The registry's entry, the file as it is now and the scope it is read through."""
        entry = adoption.registry.get(artifact)
        if entry is None:
            return None
        folders = [Path(f) for f in entry["folders"]] or [settings.workspace_root]
        scope = state.thread_files.scope_of_folders(folders[0], folders[1:])
        file = describe_artifact(scope, entry["location"])
        return None if file is None else (entry, file, scope)

    async def list_artifacts() -> list[dict[str, Any]]:
        await adoption.adopt()
        found = (described(entry["id"]) for entry in adoption.registry.entries())
        artifacts = [
            {"id": entry["id"], **{k: file[k] for k in _LISTED}}
            for entry, file, _ in (d for d in found if d)
        ]
        artifacts.sort(key=lambda a: a["modified_at"], reverse=True)
        return artifacts

    async def thumbnail(artifact: str) -> Response:
        found = described(artifact)
        if found is None or found[1]["kind"] != "slides":
            return JSONResponse({"error": "No thumbnail"}, status_code=404)
        deck = Path(found[0]["location"])
        svg = await asyncio.to_thread(slide_svg, deck, 0, found[2].root)
        if isinstance(svg, Response) and svg.status_code == 409:
            svg = await asyncio.to_thread(foreign_slide_svg, deck, 0, settings.state_dir)
        if isinstance(svg, Response):
            return svg
        return Response(svg, media_type="image/svg+xml", headers=_SVG_HEADERS)

    async def open_artifact(artifact: str) -> JSONResponse:
        """The conversation to show the artifact in and its path there: the one that made it
        while it exists, else a new one working in the folders that one did."""
        found = described(artifact)
        if found is None:
            return JSONResponse({"error": "No such artifact"}, status_code=404)
        entry, file, _ = found
        thread_id = entry["thread_id"]
        checkpointer = state.checkpointer_holder["checkpointer"]
        await checkpointer.setup()
        cursor = await checkpointer.conn.execute(
            "SELECT 1 FROM checkpoints WHERE thread_id = ? LIMIT 1", (thread_id,)
        )
        if await cursor.fetchone() is None:
            thread_id = uuid.uuid4().hex[:8]
            state.thread_files.write_workspace_sidecar(thread_id, entry["folders"])
        return JSONResponse({"thread_id": thread_id, "path": file["path"]})

    router.add_api_route("/api/artifacts", list_artifacts, methods=["GET"])
    router.add_api_route("/api/artifacts/{artifact}/thumbnail", thumbnail, methods=["GET"])
    router.add_api_route("/api/artifacts/{artifact}/open", open_artifact, methods=["POST"])
    return router
