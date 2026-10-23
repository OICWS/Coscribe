"""A Design artifact's file (an .html page, drawings inline as SVG), served for a frame to show."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

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


def design_response(file: Path, *, for_print: bool = False) -> Response:
    """The design file with the policy that keeps it inside its frame."""
    media = _MEDIA.get(file.suffix.lower())
    if media is None or not file.is_file():
        return JSONResponse({"error": "No design at that path"}, status_code=404)
    try:
        if file.stat().st_size > _MAX_BYTES:
            return JSONResponse({"error": "This design is too large to show"}, status_code=413)
        body = file.read_bytes()
    except OSError:
        return JSONResponse({"error": "This design could not be read"}, status_code=404)
    if for_print:
        body += _PRINT_HOOK
    return Response(body, media_type=media, headers=_HEADERS)


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    async def get_design(thread_id: str, path: str, print: bool = False) -> Response:
        try:
            file = state.get_session(thread_id).workspace_scope().resolve(path)
        except (PermissionError, OSError, ValueError):
            return JSONResponse({"error": "No design at that path"}, status_code=404)
        return design_response(file, for_print=print)

    router.add_api_route("/api/threads/{thread_id}/design", get_design, methods=["GET"])
    return router
