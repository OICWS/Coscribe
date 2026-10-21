"""The Docs editor's routes: a .docx read as blocks, and the changed blocks saved back
(decision 0019)."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from ...tools import (
    BlocksRefused,
    DocChanged,
    VersionGone,
    read_doc_blocks,
    read_doc_image,
    remember_before_edit,
    remember_version,
    restore_version,
    save_doc_blocks,
)
from ..schemas import DocBlocksSave, DocRestore
from ..state import AppState

# Fixed texts: a parser's own message can carry paths and internals.
_NO_DOC = "No Word document at that path"
_UNREADABLE = "This document could not be read"
_GONE = "That version is no longer kept"
_RELATIONSHIP_ID = re.compile(r"rId\d+")
_CHANGED = "This document changed since it was opened; it has been read again"


def _docx_file(state: AppState, thread_id: str, path: str, *, write: bool) -> Path | None:
    try:
        file = state.get_session(thread_id).workspace_scope().resolve(path, write=write)
    except (PermissionError, OSError, ValueError):
        return None
    return file if file.is_file() and file.suffix.lower() == ".docx" else None


def _picture_and_version_routes(router: APIRouter, state: AppState) -> None:
    async def get_image(thread_id: str, path: str, rid: str) -> Response:
        file = _docx_file(state, thread_id, path, write=False)
        if file is None or not _RELATIONSHIP_ID.fullmatch(rid):
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            image = await asyncio.to_thread(read_doc_image, file, rid)
        except Exception:
            return JSONResponse({"error": _UNREADABLE}, status_code=422)
        if image is None:
            return JSONResponse({"error": "No such picture"}, status_code=404)
        data, media_type = image
        # The url carries the file's version, so a changed picture is a new url.
        headers = {"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"}
        return Response(data, media_type=media_type, headers=headers)

    async def restore(thread_id: str, body: DocRestore) -> JSONResponse:
        file = _docx_file(state, thread_id, body.path, write=True)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            restored = await asyncio.to_thread(
                restore_version, file, state.settings.state_dir, body.version, body.to
            )
        except DocChanged:
            return JSONResponse({"error": _CHANGED, "changed": True}, status_code=409)
        except VersionGone:
            return JSONResponse({"error": _GONE}, status_code=404)
        except Exception:
            return JSONResponse({"error": _UNREADABLE}, status_code=422)
        return JSONResponse(restored)

    router.add_api_route("/api/threads/{thread_id}/docs/restore", restore, methods=["POST"])
    router.add_api_route("/api/threads/{thread_id}/docs/image", get_image, methods=["GET"])


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    async def get_blocks(thread_id: str, path: str) -> JSONResponse:
        file = _docx_file(state, thread_id, path, write=False)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            read = await asyncio.to_thread(read_doc_blocks, file)
            await asyncio.to_thread(remember_version, file, state.settings.state_dir, "seen")
            return JSONResponse(read)
        except Exception:  # a file python-docx cannot open raises many kinds of error
            return JSONResponse({"error": _UNREADABLE}, status_code=422)

    async def put_blocks(thread_id: str, body: DocBlocksSave) -> JSONResponse:
        file = _docx_file(state, thread_id, body.path, write=True)
        if file is None:
            return JSONResponse({"error": _NO_DOC}, status_code=404)
        try:
            # The file as it is before the first save since coscribe was told, to tell it later.
            await asyncio.to_thread(remember_before_edit, file, state.settings.state_dir)
            await asyncio.to_thread(remember_version, file, state.settings.state_dir, "seen")
            saved = await asyncio.to_thread(save_doc_blocks, file, body.version, body.blocks)
            await asyncio.to_thread(remember_version, file, state.settings.state_dir, "you")
        except DocChanged:
            return JSONResponse({"error": _CHANGED, "changed": True}, status_code=409)
        except BlocksRefused as refused:
            return JSONResponse({"error": refused.args[0]}, status_code=400)
        except Exception:
            return JSONResponse({"error": _UNREADABLE}, status_code=422)
        return JSONResponse(saved)

    router.add_api_route("/api/threads/{thread_id}/docs/blocks", get_blocks, methods=["GET"])
    router.add_api_route("/api/threads/{thread_id}/docs/blocks", put_blocks, methods=["PUT"])
    _picture_and_version_routes(router, state)
    return router
