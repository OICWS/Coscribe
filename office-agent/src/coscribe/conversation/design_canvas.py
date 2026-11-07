"""A Design canvas: artboards placed on a canvas, as the app shows a design. The canvas is a JSON
file; each artboard is a self-contained HTML page in the folder beside it, drawn in its own
sandboxed frame. It sits with the artifact registry, which lists a canvas as a design.

    poster.design.json      {"boards": [{id, title, file, x, y, width, height}],
                             "variables": [{name, value, label}],
                             "notes": [{id, text, x, y, width, color}]}
    poster.design           the folder beside it, holding
      main.html             one page per artboard, named by its `file`
      tab-bar.part.html     a part several pages share, placed in each with
                            `<coscribe-part name="tab-bar"></coscribe-part>`
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

CANVAS_SUFFIX = ".design.json"
_ID = re.compile(r"[\w-]{1,64}")
_FILE = re.compile(r"[\w.-]{1,120}\.html?", re.IGNORECASE)
_GAP = 80
_DEFAULT_SIZE = (1280, 800)
_NOTE_COLOURS = ("yellow", "pink", "blue", "green")
_VARIABLE = re.compile(r"--[\w-]{1,64}")
# A value goes into a style element: nothing that could end the declaration, the rule or the
# element, or open a comment that swallows the rest.
_VALUE = re.compile(r"(?!.*/\*)[^;{}<>\\]{1,200}")


class CanvasError(ValueError):
    """A canvas that cannot be read or a change that cannot be made; the text is safe to show."""


def is_canvas(path: str | Path) -> bool:
    return str(path).lower().endswith(CANVAS_SUFFIX)


def canvas_name(path: Path) -> str:
    return path.name[: -len(CANVAS_SUFFIX)]


def canvas_folder(path: Path) -> Path:
    return path.with_name(f"{canvas_name(path)}.design")


def canvas_of_page(path: Path) -> Path | None:
    """The canvas an artboard's page belongs to, or None for a page of its own."""
    folder = path.parent
    canvas = folder.with_name(folder.name + ".json")
    return canvas if folder.name.endswith(".design") and canvas.is_file() else None


def in_canvas_folder(path: Path) -> bool:
    """An artboard's page belongs to its canvas, not a design of its own."""
    return canvas_of_page(path) is not None


def _number(value: Any, fallback: float, low: float = -1e6, high: float = 1e6) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return fallback
    return float(min(max(value, low), high))


def _board(raw: Any, index: int, left: float) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CanvasError(f"Board {index + 1} is not an object")
    board_id = str(raw.get("id") or f"board-{index + 1}")
    file = raw.get("file")
    if not _ID.fullmatch(board_id):
        raise CanvasError(f"Board id {board_id!r} has characters a plain id does not")
    if not isinstance(file, str) or not _FILE.fullmatch(file):
        raise CanvasError(f"Board {board_id!r} needs `file`, an .html name in the canvas folder")
    width = _number(raw.get("width"), _DEFAULT_SIZE[0], 40, 20000)
    height = _number(raw.get("height"), _DEFAULT_SIZE[1], 40, 20000)
    return {
        "id": board_id,
        "title": str(raw.get("title") or board_id),
        "file": file,
        "x": _number(raw.get("x"), left),
        "y": _number(raw.get("y"), 0),
        "width": width,
        "height": height,
    }


def _note(raw: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not str(raw.get("text") or "").strip():
        return None
    colour = raw.get("color") if raw.get("color") in _NOTE_COLOURS else "yellow"
    return {
        "id": str(raw.get("id") or f"note-{index + 1}")[:64],
        "text": str(raw["text"])[:2000],
        "x": _number(raw.get("x"), 0),
        "y": _number(raw.get("y"), -200),
        "width": _number(raw.get("width"), 220, 80, 800),
        "color": colour,
    }


def _variable(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    name, value = raw.get("name"), raw.get("value")
    if not isinstance(name, str) or not _VARIABLE.fullmatch(name):
        return None
    if not isinstance(value, str) or not _VALUE.fullmatch(value.strip()):
        return None
    return {"name": name, "value": value.strip(), "label": str(raw.get("label") or name[2:])[:80]}


def _parse(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("boards"), list):
        raise CanvasError("A canvas is an object with a `boards` list")
    boards: list[dict[str, Any]] = []
    left = 0.0
    for index, item in enumerate(raw["boards"]):
        board = _board(item, index, left)
        boards.append(board)
        left = board["x"] + board["width"] + _GAP
    ids = [b["id"] for b in boards]
    if len(set(ids)) != len(ids):
        raise CanvasError("Two boards have the same id")
    notes = [n for i, item in enumerate(raw.get("notes") or []) if (n := _note(item, i))]
    variables: dict[str, dict[str, str]] = {}
    for item in raw.get("variables") or []:
        if variable := _variable(item):
            variables[variable["name"]] = variable
    return {"boards": boards, "variables": list(variables.values()), "notes": notes}


def read_canvas(path: Path) -> dict[str, Any]:
    """The canvas with every board's place and size filled in: a board without `x` goes to the right
    of the one before it, so a model may list boards and leave the layout to the app."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CanvasError(f"{path.name} is not valid JSON") from exc
    return _parse(raw)


PART_SUFFIX = ".part.html"
_PART_TAG = re.compile(
    rb"""<coscribe-part\s+name\s*=\s*["']?([\w-]{1,64})["']?\s*>\s*</coscribe-part\s*>""",
    re.IGNORECASE,
)
_MAX_PART = 512 * 1024


def with_parts(page: Path, body: bytes) -> bytes:
    """The page with each part it places filled in from the canvas folder. The filled part stays in
    a `coscribe-part` element laid out as if it were not there (`display: contents`), so the page's
    other elements keep the places they have in the source, which the properties panel's edits
    count by. A part does not place parts; a missing one is drawn as a marked gap, so a look at
    the page shows it."""

    def fill(match: re.Match[bytes]) -> bytes:
        name = match.group(1)
        try:
            inner = (page.parent / f"{name.decode()}{PART_SUFFIX}").read_bytes()[:_MAX_PART]
        except OSError:
            inner = (
                b'<div style="padding:8px;border:2px dashed #d33;color:#d33;font:13px sans-serif">'
                b"Missing part: " + name + b"</div>"
            )
        start = b'<coscribe-part name="' + name + b'" style="display:contents">'
        return start + inner + b"</coscribe-part>"

    return _PART_TAG.sub(fill, body)


_PICTURE_MEDIA = {
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
# A picture named by a plain file name of the canvas folder (or a folder in it), never a path
# out of it or an address; the frame loads only data: URIs, so the server fills them in.
_PICTURE_SRC = re.compile(
    rb"""(<(?:img|image)\b[^>]*?\s(?:src|href)\s*=\s*)(["'])([\w.-]+(?:/[\w.-]+)*\.(?:svg|png|jpe?g|webp|gif))\2""",
    re.IGNORECASE,
)
_MAX_PICTURES_BYTES = 12 * 1024 * 1024


def with_pictures(page: Path, body: bytes) -> bytes:
    """The page with each picture file of its canvas folder it names (`<img src="logo.svg">`,
    SVG's `<image href>`) put in as a data: URI. A name that is not a file there is left as it
    is, so a look at the page shows the gap."""
    folder = page.parent.resolve()
    budget = [_MAX_PICTURES_BYTES]

    def fill(match: re.Match[bytes]) -> bytes:
        found = _picture_file(folder, match.group(3).decode())
        if found is None:
            return match.group(0)
        data, media = found
        if len(data) > budget[0]:
            return match.group(0)
        budget[0] -= len(data)
        uri = f"data:{media};base64,{base64.b64encode(data).decode()}".encode()
        return match.group(1) + match.group(2) + uri + match.group(2)

    return _PICTURE_SRC.sub(fill, body)


def placed_pictures(page: Path, body: bytes) -> set[str]:
    """The sha256 of each picture file `body` (a page of the canvas folder, its parts filled in)
    places, by the rule `with_pictures` fills them in by."""
    folder = page.parent.resolve()
    found = (_picture_file(folder, m.group(3).decode()) for m in _PICTURE_SRC.finditer(body))
    return {hashlib.sha256(f[0]).hexdigest() for f in found if f is not None}


def _picture_file(folder: Path, name: str) -> tuple[bytes, str] | None:
    """A picture file of `folder` (or a folder inside it) with its media type; None for any other
    name, one that leaves the folder, or a missing file."""
    file = (folder / name).resolve()
    media = _PICTURE_MEDIA.get(file.suffix.lower())
    if media is None or ".." in name.split("/") or not file.is_relative_to(folder):
        return None
    try:
        return file.read_bytes(), media
    except OSError:
        return None


# A link from one artboard to another (`<a href="checkout.html">`) can't navigate the sandboxed
# frame to it, so the click is handed to the panel, which shows that board: a clickable prototype.
BOARD_LINKS = (
    b"<script>document.addEventListener('click',function(e){"
    b"var a=e.target&&e.target.closest&&e.target.closest('a[href]');if(!a)return;"
    b"var h=a.getAttribute('href')||'';if(!/^[\\w.-]+\\.html?(#.*)?$/i.test(h))return;"
    b"e.preventDefault();parent.postMessage({coscribe:'go',file:h.split('#')[0]},'*')},true)"
    b"</script>"
)


# The panel's inspector reads an artboard's elements through it; see the file for why by message.
BOARD_INSPECTOR = (
    b"<script>" + Path(__file__).with_name("board_inspector.js").read_bytes() + b"</script>"
)


def variables_style(canvas: dict[str, Any]) -> bytes:
    """The canvas's variables as a style element for each artboard's page. It goes last in the
    head, so the canvas's value wins over one the page declares itself: the canvas holds the
    design system every artboard shares, and the panel edits it in one place."""
    if not canvas["variables"]:
        return b""
    rules = ";".join(f"{v['name']}:{v['value']}" for v in canvas["variables"])
    return f"<style data-coscribe-variables>:root{{{rules}}}</style>".encode()


_SCHEME_QUERY = re.compile(rb"prefers-color-scheme\s*:\s*(dark|light)", re.IGNORECASE)


def in_scheme(body: bytes, scheme: str) -> bytes:
    """A page served light or dark, as the canvas shows its artboards. A frame cannot set the
    `prefers-color-scheme` a sandboxed page sees, so the page's own queries are answered here (in
    its styles and its scripts alike) and `data-theme` is set on its root for pages that style
    by that instead."""
    if scheme not in ("light", "dark"):
        return body
    want = scheme.encode()

    def answer(match: re.Match[bytes]) -> bytes:
        return b"min-width:0px" if match.group(1).lower() == want else b"max-width:-1px"

    head = (
        f"<style>:root{{color-scheme:{scheme}}}</style><script>"
        f"document.documentElement.setAttribute('data-theme','{scheme}')</script>"
    ).encode()
    return head + _SCHEME_QUERY.sub(answer, body)


def place_on_canvas(
    path: Path,
    boards: dict[str, dict[str, Any]],
    notes: list[dict[str, Any]] | None,
    variables: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Moves and resizes the boards named (other fields of the file stay as they are), sets the
    values of variables the canvas declares and, when given, replaces the notes: what the person
    does on the canvas. A board or variable that is gone is skipped, since the file may have been
    rewritten while the person dragged."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CanvasError(f"{path.name} is not valid JSON") from exc
    current = _parse(raw)
    by_id = {b["id"]: b for b in current["boards"]}
    for board in raw["boards"]:
        if not isinstance(board, dict):
            continue
        moved = boards.get(str(board.get("id") or ""))
        if moved is None or str(board.get("id")) not in by_id:
            continue
        for key in ("x", "y", "width", "height"):
            if key in moved:
                low, high = (40, 20000) if key in ("width", "height") else (-1e6, 1e6)
                board[key] = _number(moved[key], by_id[board["id"]][key], low, high)
    for item in raw.get("variables") or []:
        value = (variables or {}).get(str(item.get("name"))) if isinstance(item, dict) else None
        if isinstance(value, str) and _VALUE.fullmatch(value.strip()):
            item["value"] = value.strip()
    if notes is not None:
        raw["notes"] = [n for i, item in enumerate(notes) if (n := _note(item, i))]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return _parse(raw)
