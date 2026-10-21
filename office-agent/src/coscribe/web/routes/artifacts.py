"""The Artifacts page: the decks, documents and spreadsheets coscribe made, kept apart from
the conversations that made them."""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from ...conversation import (
    ArtifactFileError,
    copy_file,
    describe_artifact,
    open_in_os,
    rename_file,
    trash_file,
)
from ...tools import WorkspaceScope, foreign_slide_svg, slide_svg
from ..artifact_adoption import ArtifactAdoption
from ..schemas import ArtifactRename, ArtifactShow
from ..state import AppState
from .slides import _SVG_HEADERS

_NOT_DONE = "The file could not be changed; it may be open in another program"
_LISTED = ("path", "location", "name", "kind", "modified_at", "excerpt")
# The registry's entry, the file as it is now and the scope it is read through.
_Found = tuple[dict[str, Any], dict[str, Any], WorkspaceScope]


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    adoption = ArtifactAdoption(
        settings, state.thread_files, state.sessions, state.checkpointer_holder
    )

    def described(artifact: str) -> _Found | None:
        return _described(state, adoption, artifact)

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

    _file_routes(router, state, adoption)
    _open_routes(router, state, adoption)
    router.add_api_route("/api/artifacts", list_artifacts, methods=["GET"])
    router.add_api_route("/api/artifacts/{artifact}/thumbnail", thumbnail, methods=["GET"])
    router.add_api_route("/api/artifacts/{artifact}/open", open_artifact, methods=["POST"])
    return router


def _described(state: AppState, adoption: ArtifactAdoption, artifact: str) -> _Found | None:
    entry = adoption.registry.get(artifact)
    if entry is None:
        return None
    folders = [Path(f) for f in entry["folders"]] or [state.settings.workspace_root]
    scope = state.thread_files.scope_of_folders(folders[0], folders[1:])
    file = describe_artifact(scope, entry["location"])
    return None if file is None else (entry, file, scope)


def _summary(state: AppState, adoption: ArtifactAdoption, artifact: str) -> dict[str, Any]:
    found = _described(state, adoption, artifact)
    assert found is not None
    return {"id": artifact, **{k: found[1][k] for k in _LISTED}}


def _refused(error: Exception) -> JSONResponse:
    # A system error's text can carry paths and internals; only our own refusals are shown.
    text = str(error) if isinstance(error, ArtifactFileError) else _NOT_DONE
    return JSONResponse({"error": text}, status_code=409)


def _missing() -> JSONResponse:
    return JSONResponse({"error": "No such artifact"}, status_code=404)


def _file_routes(router: APIRouter, state: AppState, adoption: ArtifactAdoption) -> None:
    """What the menu does to the file: rename, copy, move to the recycle bin."""
    registry = adoption.registry

    async def rename(artifact: str, body: ArtifactRename) -> JSONResponse:
        found = _described(state, adoption, artifact)
        if found is None:
            return _missing()
        try:
            target = await asyncio.to_thread(rename_file, Path(found[0]["location"]), body.name)
        except (ArtifactFileError, OSError) as error:
            return _refused(error)
        registry.update(artifact, location=str(target))
        return JSONResponse(_summary(state, adoption, artifact))

    async def duplicate(artifact: str) -> JSONResponse:
        found = _described(state, adoption, artifact)
        if found is None:
            return _missing()
        try:
            target = await asyncio.to_thread(copy_file, Path(found[0]["location"]))
        except (ArtifactFileError, OSError) as error:
            return _refused(error)
        entry = found[0]
        registry.adopt([str(target)], entry["folders"], entry["thread_id"])
        return JSONResponse(
            _summary(
                state,
                adoption,
                next(e["id"] for e in registry.entries() if e["location"] == str(target)),
            )
        )

    async def delete(artifact: str) -> JSONResponse:
        found = _described(state, adoption, artifact)
        if found is None:
            return _missing()
        try:
            await asyncio.to_thread(trash_file, Path(found[0]["location"]))
        except OSError as error:
            return _refused(error)
        registry.remove(artifact)
        return JSONResponse({"deleted": artifact})

    router.add_api_route("/api/artifacts/{artifact}/rename", rename, methods=["POST"])
    router.add_api_route("/api/artifacts/{artifact}/duplicate", duplicate, methods=["POST"])
    router.add_api_route("/api/artifacts/{artifact}", delete, methods=["DELETE"])


def _open_routes(router: APIRouter, state: AppState, adoption: ArtifactAdoption) -> None:
    """Finding the artifact a panel shows, and handing the file to its program."""
    registry = adoption.registry

    async def lookup(thread_id: str, path: str) -> JSONResponse:
        """The artifact a panel is showing, when coscribe made the file it shows."""
        try:
            location = state.get_session(thread_id).workspace_scope().resolve(path)
        except (PermissionError, OSError, ValueError):
            return _missing()
        entry = next(
            (
                e
                for e in registry.entries()
                if os.path.normcase(e["location"]) == os.path.normcase(str(location))
            ),
            None,
        )
        if entry is None or _described(state, adoption, entry["id"]) is None:
            return _missing()
        return JSONResponse(_summary(state, adoption, entry["id"]))

    async def show(artifact: str, body: ArtifactShow) -> JSONResponse:
        found = _described(state, adoption, artifact)
        if found is None:
            return _missing()
        try:
            open_in_os(Path(found[0]["location"]), reveal=body.reveal)
        except OSError as error:
            return _refused(error)
        return JSONResponse({"ok": True})

    router.add_api_route("/api/artifacts/lookup", lookup, methods=["GET"])
    router.add_api_route("/api/artifacts/{artifact}/show", show, methods=["POST"])
