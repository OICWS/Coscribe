"""A Design or Dashboard artifact's page (an .html file), served for a frame to show; a dashboard
gets its datasets and chart library put into it, since the frame has no network."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ...conversation import (
    CanvasError,
    DashboardDataError,
    canvas_folder,
    is_canvas,
    is_dashboard,
    place_on_canvas,
    read_canvas,
    read_dashboard_data,
    served_page,
)
from ..state import AppState

_MEDIA = {".html": "text/html; charset=utf-8"}
_MAX_BYTES = 8 * 1024 * 1024
# The page may run its own script and style but has no origin of its own and no way out: no
# network, no frames, no forms, no navigation. That is what lets the app show a page a model wrote.
_POLICY = (
    "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; img-src data: blob:; font-src data:; media-src data: blob:"
)
_HEADERS = {
    "Content-Security-Policy": _POLICY,
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}


# Added to the copy served for printing: the page prints when the app asks and says when it is
# done. The page has no other way to be told, because its frame has no origin to message.
_PRINT_HOOK = (
    b"<script>addEventListener('message',function(e){if(e.source!==parent||e.data!=='coscribe-print')"
    b"return;addEventListener('afterprint',function(){parent.postMessage('coscribe-printed','*')},"
    b"{once:true});setTimeout(function(){print()},50)})</script>"
)


def canvas_cover(file: Path) -> Path:
    """A canvas stands for its first artboard where one page is shown (a card, a download)."""
    try:
        boards = read_canvas(file)["boards"]
    except CanvasError:
        return file
    return canvas_folder(file) / boards[0]["file"] if boards else file


def design_response(file: Path, *, for_print: bool = False, scheme: str | None = None) -> Response:
    """The design file with the policy that keeps it inside its frame."""
    if is_canvas(file):
        file = canvas_cover(file)
    media = _MEDIA.get(file.suffix.lower())
    if media is None or not file.is_file():
        return JSONResponse({"error": "No design at that path"}, status_code=404)
    try:
        if file.stat().st_size > _MAX_BYTES:
            return JSONResponse({"error": "This design is too large to show"}, status_code=413)
        body = served_page(file, file.read_bytes(), scheme)
    except OSError:
        return JSONResponse({"error": "This design could not be read"}, status_code=404)
    if for_print:
        body += _PRINT_HOOK
    return Response(body, media_type=media, headers=_HEADERS)


class CanvasPlacement(BaseModel):
    # Board id -> any of x, y, width, height.
    boards: dict[str, dict[str, float]] = {}
    notes: list[dict[str, Any]] | None = None
    # Variable name -> its new value; only variables the canvas declares change.
    variables: dict[str, str] = {}


def _with_board_paths(path: str, file: Path, canvas: dict[str, Any]) -> dict[str, Any]:
    """Each board with the workspace path its page is served by, beside the canvas file."""
    folder = PurePosixPath(path.replace("\\", "/")).parent / canvas_folder(file).name
    boards = [{**b, "path": str(folder / b["file"])} for b in canvas["boards"]]
    return {**canvas, "boards": boards}


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    async def get_design(
        thread_id: str,
        path: str,
        print: bool = False,
        scheme: Literal["light", "dark"] | None = None,
    ) -> Response:
        try:
            file = state.get_session(thread_id).workspace_scope().resolve(path)
        except (PermissionError, OSError, ValueError):
            return JSONResponse({"error": "No design at that path"}, status_code=404)
        return design_response(file, for_print=print, scheme=scheme)

    async def get_dashboard(thread_id: str, path: str) -> JSONResponse:
        """What the panel shows above a dashboard: its datasets, where each came from and when;
        404 for a page that is not a dashboard."""
        try:
            file = state.get_session(thread_id).workspace_scope().resolve(path)
            with file.open("rb") as page:
                marked = is_dashboard(page.read(8192))
        except (PermissionError, OSError, ValueError):
            marked = False
        if not marked:
            return JSONResponse({"error": "No dashboard at that path"}, status_code=404)
        try:
            data = read_dashboard_data(file)
        except DashboardDataError:
            # The page itself is told why (`window.coscribe.error`); the panel only says it failed.
            return JSONResponse({"datasets": [], "error": "The dashboard's data could not be read"})
        datasets = [
            {
                "id": name,
                "title": info.get("title") or name,
                "source": info.get("source"),
                "updated": info.get("updated"),
                "rows": len(info["rows"]),
            }
            for name, info in data["datasets"].items()
        ]
        return JSONResponse({"datasets": datasets, "error": None})

    def canvas_file(thread_id: str, path: str) -> Path | None:
        try:
            file = state.get_session(thread_id).workspace_scope().resolve(path)
        except (PermissionError, OSError, ValueError):
            return None
        return file if is_canvas(file) and file.is_file() else None

    async def get_canvas(thread_id: str, path: str) -> JSONResponse:
        """A Design canvas: its boards (each with the path its page is served by) and notes."""
        file = canvas_file(thread_id, path)
        if file is None:
            return JSONResponse({"error": "No canvas at that path"}, status_code=404)
        try:
            canvas = read_canvas(file)
        except CanvasError:
            # The panel says only that it failed; coscribe reads the file itself to find why.
            return JSONResponse({"error": "The canvas file could not be read"}, status_code=422)
        return JSONResponse(_with_board_paths(path, file, canvas))

    async def put_canvas(thread_id: str, path: str, body: CanvasPlacement) -> JSONResponse:
        """What the person did on the canvas: boards moved or resized, variables set, notes
        changed."""
        file = canvas_file(thread_id, path)
        if file is None:
            return JSONResponse({"error": "No canvas at that path"}, status_code=404)
        try:
            canvas = place_on_canvas(file, body.boards, body.notes, body.variables)
        except CanvasError:
            return JSONResponse({"error": "The canvas file could not be read"}, status_code=422)
        return JSONResponse(_with_board_paths(path, file, canvas))

    router.add_api_route("/api/threads/{thread_id}/design", get_design, methods=["GET"])
    router.add_api_route("/api/threads/{thread_id}/canvas", get_canvas, methods=["GET"])
    router.add_api_route("/api/threads/{thread_id}/canvas", put_canvas, methods=["PUT"])
    router.add_api_route("/api/threads/{thread_id}/dashboard", get_dashboard, methods=["GET"])
    return router
