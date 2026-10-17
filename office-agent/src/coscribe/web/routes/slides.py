"""The Slides panel's reads: a deck built from pages, and one slide of it as an SVG
(decision 0016). Read only; the panel's edits come with the section editor."""

from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from ...tools import NotBuiltFromPages, read_deck, slide_svg
from ..state import AppState

# The SVG is drawn by the panel as an image, which runs nothing; this keeps it inert too when
# it is opened on its own, since it is served from the app's origin.
_SVG_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; img-src data:; style-src 'unsafe-inline'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    def deck_file(thread_id: str, path: str) -> tuple[Path, Path] | None:
        """The deck and the workspace it may draw pictures from, when `path` is a .pptx there."""
        try:
            scope = state.get_session(thread_id).workspace_scope()
            deck = scope.resolve(path)
        except (PermissionError, OSError, ValueError):
            return None
        if not deck.is_file() or deck.suffix.lower() != ".pptx":
            return None
        return deck, Path(scope.root)

    async def get_slides(thread_id: str, path: str) -> Any:
        found = deck_file(thread_id, path)
        if found is None:
            return JSONResponse({"error": f"No deck {path!r}"}, status_code=404)
        try:
            return await asyncio.to_thread(read_deck, found[0])
        except NotBuiltFromPages as exc:
            return JSONResponse({"error": str(exc), "built": False}, status_code=409)
        except (ValueError, zipfile.BadZipFile) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def get_slide_svg(thread_id: str, index: int, path: str) -> Response:
        found = deck_file(thread_id, path)
        if found is None:
            return JSONResponse({"error": f"No deck {path!r}"}, status_code=404)
        try:
            svg = await asyncio.to_thread(slide_svg, found[0], index, found[1])
        except IndexError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        except NotBuiltFromPages as exc:
            return JSONResponse({"error": str(exc), "built": False}, status_code=409)
        except (ValueError, SyntaxError, zipfile.BadZipFile) as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return Response(svg, media_type="image/svg+xml", headers=_SVG_HEADERS)

    router.add_api_route("/api/threads/{thread_id}/slides", get_slides, methods=["GET"])
    router.add_api_route(
        "/api/threads/{thread_id}/slides/{index}/svg", get_slide_svg, methods=["GET"]
    )
    return router
