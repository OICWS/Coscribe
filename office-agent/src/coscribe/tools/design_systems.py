"""The person's design systems (decision 0020): a library kept in the app's data directory, one
folder per system holding `system.json`. A conversation that makes a deck gets a copy; nothing
here refers back to a deck, so changing a system never moves a finished one.

What a system holds: colors (named roles), typography (installed fonts and named text styles),
spacing, corner radius, and an overview in free text that the model reads.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._file_locks import file_lock, replace_with_retry

SYSTEM_FILE = "system.json"
# An id comes from a URL, so it must never name a path outside the library.
_SAFE_ID = re.compile(r"[a-f0-9]{10}")
_COLOUR = re.compile(r"#[0-9a-fA-F]{6}")
_MAX_NAME = 80
_MAX_OVERVIEW = 20_000
_MAX_ROWS = 60
_MAX_TEXT = 200
# How many colors a listing carries for a card to draw.
_SWATCHES = 8

# What a new system starts with, so its form is not empty: a neutral palette and the six text
# styles a deck needs (size in px on the 1920 canvas, weight, line height, letter spacing in px).
_COLORS = [
    ("Background", "#FFFFFF", "Page background"),
    ("Text", "#1F2937", "Body text"),
    ("Muted text", "#6B7280", "Captions and secondary text"),
    ("Accent", "#2563EB", "Links, key figures and highlights"),
]
_STYLES = [
    ("heading-1", "Heading 1", 144, 700, 1.1, 0),
    ("heading-3", "Heading 3", 44, 700, 1.2, 0),
    ("lead", "Lead", 44, 400, 1.3, 0),
    ("eyebrow", "Eyebrow", 24, 700, 1.2, 3),
    ("body", "Body", 32, 400, 1.4, 0),
    ("caption", "Caption", 24, 400, 1.3, 0),
]


class DesignSystemError(ValueError):
    """A system that cannot be saved as given; the message says why."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: Any, what: str, limit: int = _MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise DesignSystemError(f"{what} must be text")
    text: str = value.strip()
    if len(text) > limit:
        raise DesignSystemError(f"{what} is longer than {limit} characters")
    return text


def _number(value: Any, what: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not low <= value <= high:
        raise DesignSystemError(f"{what} must be a number from {low} to {high}")
    return value


def _rows(value: Any, what: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise DesignSystemError(f"{what} must be a list")
    if len(value) > _MAX_ROWS:
        raise DesignSystemError(f"{what} has more than {_MAX_ROWS} rows")
    return value


def _named_values(value: Any, what: str) -> list[dict[str, str]]:
    return [
        {
            "name": _text(row.get("name", ""), f"a {what} name"),
            "value": _text(row.get("value", ""), f"a {what} value"),
        }
        for row in _rows(value, what)
    ]


def _colors(value: Any) -> list[dict[str, str]]:
    colors = []
    for row in _rows(value, "colors"):
        colour = _text(row.get("value", ""), "a color")
        if not _COLOUR.fullmatch(colour):
            raise DesignSystemError(f"{colour!r} is not a color like #1F2937")
        colors.append(
            {
                "name": _text(row.get("name", ""), "a color name"),
                "value": colour.upper(),
                "note": _text(row.get("note", ""), "a color note"),
            }
        )
    return colors


def _styles(value: Any) -> list[dict[str, Any]]:
    styles = []
    for row in _rows(value, "text styles"):
        styles.append(
            {
                "id": _text(row.get("id", ""), "a text style id", 40),
                "name": _text(row.get("name", ""), "a text style name"),
                "size": _number(row.get("size"), "a text size", 6, 600),
                "weight": _number(row.get("weight"), "a text weight", 100, 900),
                "line_height": _number(row.get("line_height"), "a line height", 0.5, 4),
                "letter_spacing": _number(row.get("letter_spacing"), "a letter spacing", -20, 40),
            }
        )
    if len({style["id"] for style in styles}) != len(styles):
        raise DesignSystemError("two text styles share an id")
    return styles


def _typography(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DesignSystemError("typography must be an object")
    fonts = value.get("fonts", [])
    if not isinstance(fonts, list):
        raise DesignSystemError("fonts must be a list")
    return {
        "fonts": [_text(font, "a font name", 80) for font in fonts[:_MAX_ROWS]],
        "styles": _styles(value.get("styles", [])),
    }


def _clean(data: Any) -> dict[str, Any]:
    """The editable part of a system, checked and shaped; raises `DesignSystemError`."""
    if not isinstance(data, dict):
        raise DesignSystemError("a design system must be an object")
    name = _text(data.get("name", ""), "the name", _MAX_NAME)
    if not name:
        raise DesignSystemError("the name cannot be empty")
    return {
        "name": name,
        "overview": _text(data.get("overview", ""), "the overview", _MAX_OVERVIEW),
        "colors": _colors(data.get("colors", [])),
        "typography": _typography(data.get("typography", {})),
        "spacing": _named_values(data.get("spacing", []), "spacing"),
        "radius": _named_values(data.get("radius", []), "corner radius"),
    }


def _palette_of(data: dict[str, Any]) -> list[str]:
    """The system's colors as #RRGGBB, for a card to draw; what a damaged file holds is skipped."""
    colors = data.get("colors")
    rows = colors if isinstance(colors, list) else []
    values = [row.get("value") for row in rows if isinstance(row, dict)]
    return [v for v in values if isinstance(v, str) and _COLOUR.fullmatch(v)][:_SWATCHES]


class DesignSystemStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.root = Path(state_dir) / "design_systems"

    def _path(self, system_id: str) -> Path | None:
        return self.root / system_id / SYSTEM_FILE if _SAFE_ID.fullmatch(system_id) else None

    def _read(self, path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        replace_with_retry(tmp, path)

    def list_systems(self) -> list[dict[str, Any]]:
        """Id, name, first colors and last change of each system, newest change first."""
        found = []
        for path in self.root.glob(f"*/{SYSTEM_FILE}") if self.root.is_dir() else []:
            data = self._read(path)
            if data is not None and _SAFE_ID.fullmatch(path.parent.name):
                found.append(
                    {
                        "id": path.parent.name,
                        "name": str(data.get("name", "")),
                        "palette": _palette_of(data),
                        "updated_at": str(data.get("updated_at", "")),
                    }
                )
        return sorted(found, key=lambda system: system["updated_at"], reverse=True)

    def get(self, system_id: str) -> dict[str, Any] | None:
        path = self._path(system_id)
        data = self._read(path) if path is not None else None
        return None if data is None else {**data, "id": system_id}

    def create(self, name: str) -> dict[str, Any]:
        system = _clean(
            {
                "name": name,
                "colors": [{"name": n, "value": v, "note": note} for n, v, note in _COLORS],
                "typography": {
                    "fonts": [],
                    "styles": [
                        {
                            "id": i,
                            "name": n,
                            "size": s,
                            "weight": w,
                            "line_height": h,
                            "letter_spacing": ls,
                        }
                        for i, n, s, w, h, ls in _STYLES
                    ],
                },
            }
        )
        system_id = uuid.uuid4().hex[:10]
        now = _now()
        system = {**system, "created_at": now, "updated_at": now}
        path = self.root / system_id / SYSTEM_FILE
        with file_lock(path):
            self._write(path, system)
        return {**system, "id": system_id}

    def update(self, system_id: str, data: Any) -> dict[str, Any] | None:
        """Saves the editable part of a system; None when there is no such system."""
        path = self._path(system_id)
        if path is None:
            return None
        with file_lock(path):
            current = self._read(path)
            if current is None:
                return None
            system = {**current, **_clean(data), "updated_at": _now()}
            self._write(path, system)
        return {**system, "id": system_id}

    def _thread_path(self, thread_id: str) -> Path:
        # A thread id is whatever the page sent; its hash is always a safe file name.
        return (
            self.root.parent
            / "thread_design_systems"
            / f"{hashlib.sha256(thread_id.encode()).hexdigest()[:32]}.json"
        )

    def choose_for_thread(self, thread_id: str, system_id: str) -> dict[str, Any] | None:
        """A conversation that starts a deck with a system keeps a copy of it as it was then
        (decision 0020: the deck never refers back). None when there is no such system."""
        system = self.get(system_id)
        if system is None:
            return None
        path = self._thread_path(thread_id)
        with file_lock(path):
            self._write(path, system)
        return system

    def chosen_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        return self._read(self._thread_path(thread_id))

    def delete(self, system_id: str) -> bool:
        path = self._path(system_id)
        if path is None or not path.parent.is_dir():
            return False
        with file_lock(path):
            shutil.rmtree(path.parent, ignore_errors=True)
        return True


def as_deck_design_system(system: dict[str, Any]) -> dict[str, Any]:
    """A library system in the shape a deck keeps as `design-system.json`: the palette, fonts and
    text styles the Slides panel offers, with the rest of the system kept beside them."""
    return {
        **{key: value for key, value in system.items() if key != "typography"},
        "palette": [color["value"] for color in system.get("colors", [])],
        "fonts": list(system.get("typography", {}).get("fonts", [])),
        "styles": list(system.get("typography", {}).get("styles", [])),
        "source": system.get("id"),
    }
