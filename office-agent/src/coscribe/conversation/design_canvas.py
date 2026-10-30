"""A Design canvas: artboards placed on a canvas, as the app shows a design. The canvas is a JSON
file; each artboard is a self-contained HTML page in the folder beside it, drawn in its own
sandboxed frame. It sits with the artifact registry, which lists a canvas as a design.

    poster.design.json      {"boards": [{id, title, file, x, y, width, height}],
                             "variables": [{name, value, label}],
                             "notes": [{id, text, x, y, width, color}]}
    poster.design           the folder beside it, holding
      main.html             one page per artboard, named by its `file`
"""

from __future__ import annotations

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


def variables_style(canvas: dict[str, Any]) -> bytes:
    """The canvas's variables as a style element for each artboard's page. It goes last in the
    head, so the canvas's value wins over one the page declares itself: the canvas holds the
    design system every artboard shares, and the panel edits it in one place."""
    if not canvas["variables"]:
        return b""
    rules = ";".join(f"{v['name']}:{v['value']}" for v in canvas["variables"])
    return f"<style data-coscribe-variables>:root{{{rules}}}</style>".encode()


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
