"""`look_at_page`: coscribe sees a Design or Dashboard page as the app draws it, with a report of
what a look catches. The page is served as the design route serves it (`served_page`), so a canvas's
variables, a dashboard's data and the light or dark scheme are all in."""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any

from ..runtime import tool_metadata
from ..tools import WorkspaceScope
from .dashboard import is_dashboard, render_dashboard
from .design_canvas import (
    BOARD_INSPECTOR,
    BOARD_LINKS,
    CanvasError,
    canvas_folder,
    canvas_of_page,
    in_scheme,
    is_canvas,
    read_canvas,
    variables_style,
    with_parts,
)
from .page_shot import PageShotError, shoot_page

_MAX_BOARDS = 4
_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
_MAX_SIDE = 1568
_PAGE_SIZE = (1280, 800)
_LONGEST_PAGE = 4000


def served_page(page: Path, body: bytes, scheme: str | None = None) -> bytes:
    """A page as the app serves it to its frame: a dashboard with its data and chart library, an
    artboard with the parts it places filled in, its canvas's variables last in its head, its links
    to other artboards handed to the panel and the panel's inspector, in a scheme when one is asked
    for."""
    if is_dashboard(body):
        body = render_dashboard(page, body)
    canvas = canvas_of_page(page)
    if canvas is not None:
        body = with_parts(page, body)
        try:
            style = variables_style(read_canvas(canvas)) + BOARD_LINKS + BOARD_INSPECTOR
        except CanvasError:
            style = BOARD_LINKS + BOARD_INSPECTOR
        end = body.lower().find(b"</head>")
        body = body[:end] + style + body[end:] if end >= 0 else style + body
    return in_scheme(body, scheme) if scheme else body


class NotSquare(PageShotError):
    """An icon asked of an artboard that is not square."""


def export_board(page: Path, kind: str, scheme: str | None = None) -> bytes:
    """An artboard's page as a file to keep: a PNG at twice its size, or, for a square board (a
    logo, an icon), an .ico holding it at the sizes Windows asks for. Drawn as the app serves it,
    in the computer's own browser."""
    from PIL import Image

    canvas = canvas_of_page(page)
    try:
        boards = read_canvas(canvas)["boards"] if canvas is not None else []
    except CanvasError as exc:
        raise PageShotError(str(exc)) from exc
    board = next((b for b in boards if b["file"].lower() == page.name.lower()), None)
    if board is None:
        raise PageShotError("Only an artboard of a canvas is exported here")
    width, height = int(board["width"]), int(board["height"])
    if kind == "ico" and width != height:
        raise NotSquare("An icon is made from a square artboard")
    # An icon's largest size is 256 px; a smaller board is drawn denser to reach it.
    scale = 2 if kind == "png" else max(1, min(4, -(-256 // width)))
    shot = shoot_page(
        served_page(page, page.read_bytes(), scheme), width, height, fixed=True, scale=scale
    )
    if kind == "png":
        return shot.png
    out = BytesIO()
    with Image.open(BytesIO(shot.png)) as image:
        side = min(image.size)
        sizes = [(s, s) for s in _ICON_SIZES if s <= side] or [(side, side)]
        image.convert("RGBA").save(out, format="ICO", sizes=sizes)
    return out.getvalue()


def _smaller(png: bytes) -> bytes:
    """Neither side over what a vision model reads at full detail: fewer tokens, the same look."""
    from PIL import Image

    with Image.open(BytesIO(png)) as image:
        if max(image.size) <= _MAX_SIDE:
            return png
        image.thumbnail((_MAX_SIDE, _MAX_SIDE))
        out = BytesIO()
        image.save(out, format="PNG", optimize=True)
        return out.getvalue()


def _image_block(png: bytes) -> dict[str, Any]:
    data = base64.b64encode(_smaller(png)).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}


def _targets(file: Path, board: str | None) -> tuple[list[dict[str, Any]], list[str]]:
    """What to draw: each artboard of a canvas (or the one named), or the page itself."""
    if not is_canvas(file):
        width, height = _PAGE_SIZE
        return [{"id": None, "page": file, "width": width, "height": height, "fixed": False}], []
    boards = read_canvas(file)["boards"]
    if board is not None:
        boards = [b for b in boards if board in (b["id"], b["title"])]
        if not boards:
            raise ValueError(f"The canvas has no artboard {board!r}")
    folder = canvas_folder(file)
    chosen = [
        {
            "id": b["id"],
            "page": folder / b["file"],
            "width": int(b["width"]),
            "height": int(b["height"]),
            "fixed": True,
        }
        for b in boards[:_MAX_BOARDS]
    ]
    return chosen, [b["id"] for b in boards[_MAX_BOARDS:]]


def build_page_tools(scope: Callable[[], WorkspaceScope]) -> list[Callable[..., Any]]:
    """`look_at_page`, read only and deferred like the other non-core tools (0001)."""

    def look_at_page(
        path: str, board: str | None = None, scheme: str | None = None
    ) -> list[dict[str, Any]]:
        """Look at a Design canvas, a Dashboard or another .html page as the app draws it: a
        screenshot of each page and a report of script errors, loads the page tried (it has no
        network), a page wider than its board, text over text and text past a board's edge.
        Use it after writing or changing a design or dashboard, before saying it is done, and
        fix what it shows. A canvas shows each artboard (four at most per call; name one with
        `board` to look at it alone).

        Args:
            path: the .design.json canvas, or the .html page.
            board: one artboard of the canvas, by id or title.
            scheme: "light" or "dark", to see the page in that scheme.
        """
        if scheme not in (None, "light", "dark"):
            raise ValueError('scheme is "light" or "dark"')
        file = scope().resolve(path)
        if not file.is_file():
            raise ValueError(f"File does not exist: {path}")
        targets, not_shown = _targets(file, board)
        pages: list[dict[str, Any]] = []
        images: list[dict[str, Any]] = []
        for target in targets:
            page: Path = target["page"]
            if not page.is_file():
                pages.append({"board": target["id"], "problem": f"{page.name} does not exist"})
                continue
            body = served_page(page, page.read_bytes(), scheme)
            try:
                shot = shoot_page(body, target["width"], target["height"], fixed=target["fixed"])
                if not target["fixed"] and shot.report.get("content_height", 0) > target["height"]:
                    tall = min(int(shot.report["content_height"]), _LONGEST_PAGE)
                    shot = shoot_page(body, target["width"], tall, fixed=False)
            except PageShotError as exc:
                raise ValueError(str(exc)) from exc
            entry = {"size": f"{target['width']}x{target['height']}", **shot.report}
            pages.append({"board": target["id"], **entry} if target["id"] else entry)
            images.append(_image_block(shot.png))
        summary: dict[str, Any] = {"path": path, "pages": pages}
        if not_shown:
            summary["not_shown"] = not_shown
        return [{"type": "text", "text": json.dumps(summary, ensure_ascii=False)}, *images]

    return [tool_metadata(look_at_page, risk_category="READ", category="documents")]
