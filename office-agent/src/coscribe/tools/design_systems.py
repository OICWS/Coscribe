"""The person's design systems (decision 0020): a library kept in the app's data directory, one
folder per system holding `system.json`. A conversation that makes a deck gets a copy; nothing
here refers back to a deck, so changing a system never moves a finished one.

What a system holds: colors (named roles), typography (installed fonts and named text styles),
spacing, corner radius, assets (logos, icons and pictures in `assets/`, each with a note on when
to use it) and an overview in free text that the model reads.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..runtime import tool_metadata
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
ASSETS_FOLDER = "assets"
_MAX_ASSET_BYTES = 2 * 1024 * 1024
_MAX_ASSETS = 24
ASSET_KINDS = ("logo", "icon", "picture")
ASSET_MEDIA = {
    "svg": "image/svg+xml",
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}

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


def _sniffed(data: bytes) -> str | None:
    """The picture's format from its first bytes, never from the name it was given."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    head = data[:1024].lstrip().lower()
    if head.startswith((b"<?xml", b"<svg", b"<!--")) and b"<svg" in data[:4096].lower():
        return "svg"
    return None


def _picture_size(data: bytes, kind: str) -> tuple[int | None, int | None]:
    if kind == "svg":
        found = re.search(
            rb"<svg[^>]*\bviewBox\s*=\s*[\"']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)",
            data,
            re.I,
        )
        return (
            (round(float(found.group(1))), round(float(found.group(2)))) if found else (None, None)
        )
    from io import BytesIO

    from PIL import Image

    try:
        with Image.open(BytesIO(data)) as image:
            return image.size
    except OSError:
        raise DesignSystemError("the picture could not be read") from None


def _asset_fields(data: Any, current: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise DesignSystemError("an asset must be an object")
    kind = data.get("kind", current.get("kind", "logo"))
    if kind not in ASSET_KINDS:
        raise DesignSystemError(f"an asset is a {', '.join(ASSET_KINDS)}")
    name = _text(data.get("name", current.get("name", "")), "an asset name")
    if not name:
        raise DesignSystemError("an asset needs a name")
    return {
        "name": name,
        "kind": kind,
        "note": _text(data.get("note", current.get("note", "")), "an asset note"),
    }


def _file_stem(text: str) -> str:
    """A name as a plain file name: letters, digits, dashes and underscores, any script."""
    return re.sub(r"[^\w-]+", "-", text).strip("-_")[:60]


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

    def duplicate(self, system_id: str, name: str) -> dict[str, Any] | None:
        """A copy of the system under a new id, its assets with it; None when there is none."""
        path = self._path(system_id)
        current = self._read(path) if path is not None else None
        if path is None or current is None:
            return None
        made = self.create(name)
        target = self.root / made["id"]
        if (path.parent / ASSETS_FOLDER).is_dir():
            shutil.copytree(path.parent / ASSETS_FOLDER, target / ASSETS_FOLDER)
        system = {
            **current,
            "name": _text(name, "the name", _MAX_NAME),
            "created_at": made["created_at"],
        }
        system["updated_at"] = made["updated_at"]
        with file_lock(target / SYSTEM_FILE):
            self._write(target / SYSTEM_FILE, system)
        return {**system, "id": made["id"]}

    def add_asset(self, system_id: str, data: bytes, name: str) -> dict[str, Any] | None:
        """Keeps a picture with the system; None when there is no such system."""
        path = self._path(system_id)
        if path is None:
            return None
        if len(data) > _MAX_ASSET_BYTES:
            raise DesignSystemError("a picture may be at most 2 MB")
        kind = _sniffed(data)
        if kind is None:
            raise DesignSystemError("a picture is an SVG, PNG, JPEG or WebP file")
        width, height = _picture_size(data, kind)
        stem = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", name.strip())[:_MAX_TEXT] or "Picture"
        with file_lock(path):
            current = self._read(path)
            if current is None:
                return None
            assets = [a for a in current.get("assets", []) if isinstance(a, dict)]
            if len(assets) >= _MAX_ASSETS:
                raise DesignSystemError(f"a design system holds at most {_MAX_ASSETS} pictures")
            asset_id = uuid.uuid4().hex[:10]
            asset = {
                "id": asset_id,
                "file": f"{asset_id}.{kind}",
                "name": stem,
                "kind": "logo",
                "note": "",
                "width": width,
                "height": height,
            }
            folder = path.parent / ASSETS_FOLDER
            folder.mkdir(exist_ok=True)
            (folder / f"{asset_id}.{kind}").write_bytes(data)
            self._write(path, {**current, "assets": [*assets, asset], "updated_at": _now()})
        return asset

    def update_asset(self, system_id: str, asset_id: str, data: Any) -> dict[str, Any] | None:
        """Renames an asset or changes its kind or note; None when there is no such asset."""
        path = self._path(system_id)
        if path is None:
            return None
        with file_lock(path):
            current = self._read(path)
            assets = [a for a in (current or {}).get("assets", []) if isinstance(a, dict)]
            found = next((a for a in assets if a.get("id") == asset_id), None)
            if current is None or found is None:
                return None
            changed = {**found, **_asset_fields(data, found)}
            assets = [changed if a is found else a for a in assets]
            self._write(path, {**current, "assets": assets, "updated_at": _now()})
        return changed

    def delete_asset(self, system_id: str, asset_id: str) -> bool:
        path = self._path(system_id)
        if path is None:
            return False
        with file_lock(path):
            current = self._read(path)
            assets = [a for a in (current or {}).get("assets", []) if isinstance(a, dict)]
            found = next((a for a in assets if a.get("id") == asset_id), None)
            if current is None or found is None:
                return False
            kept = [a for a in assets if a is not found]
            self._write(path, {**current, "assets": kept, "updated_at": _now()})
        (path.parent / ASSETS_FOLDER / str(found.get("file", ""))).unlink(missing_ok=True)
        return True

    def asset_file(self, system_id: str, asset_id: str) -> tuple[Path, str] | None:
        """The asset's file and its media type, for the app to draw it."""
        system = self.get(system_id)
        found = next(
            (
                a
                for a in (system or {}).get("assets", [])
                if isinstance(a, dict) and a.get("id") == asset_id
            ),
            None,
        )
        if system is None or found is None:
            return None
        file = str(found.get("file", ""))
        media = ASSET_MEDIA.get(file.rsplit(".", 1)[-1])
        target = self.root / system_id / ASSETS_FOLDER / file
        return (
            (target, media)
            if media and re.fullmatch(r"[a-f0-9]{10}\.[a-z]{3,4}", file) and target.is_file()
            else None
        )

    def copy_assets(self, system_id: str, workspace: Path) -> list[dict[str, Any]]:
        """The system's pictures copied into the workspace as `brand/<system>/<name>.<ext>`, each
        entry with its workspace `path`. The copy never refers back (decision 0020): a picture
        changed in the library later does not move a deck or design made from this one."""
        system = self.get(system_id)
        if system is None:
            return []
        copied: list[dict[str, Any]] = []
        for asset, path in _brand_paths(system):
            kept = self.asset_file(system_id, str(asset.get("id", "")))
            if kept is None:
                continue
            target = workspace / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kept[0], target)
            copied.append({**asset, "path": path})
        return copied

    def deck_system_for_thread(self, thread_id: str) -> dict[str, Any] | None:
        """The system the conversation started with, in a deck's shape, each picture with the
        workspace path `copy_assets` gave its copy and the sha256 of its file: what a deck built
        in that conversation is checked against. None when it started with none."""
        chosen = self.chosen_for_thread(thread_id)
        if chosen is None:
            return None
        assets = []
        for asset, path in _brand_paths(chosen):
            entry = {**asset, "path": path}
            kept = self.asset_file(str(chosen.get("id", "")), str(asset.get("id", "")))
            if kept is not None:
                entry["sha256"] = hashlib.sha256(kept[0].read_bytes()).hexdigest()
            assets.append(entry)
        return {**as_deck_design_system(chosen), "assets": assets}

    def delete(self, system_id: str) -> bool:
        path = self._path(system_id)
        if path is None or not path.parent.is_dir():
            return False
        with file_lock(path):
            shutil.rmtree(path.parent, ignore_errors=True)
        return True


def _brand_paths(system: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """Each picture of `system` with its workspace path, `brand/<system>/<name>.<ext>`, a name
    taken twice numbered."""
    folder = _file_stem(str(system.get("name", ""))) or "design-system"
    named: list[tuple[dict[str, Any], str]] = []
    taken: set[str] = set()
    for asset in system.get("assets", []):
        if not isinstance(asset, dict):
            continue
        suffix = Path(str(asset.get("file", ""))).suffix
        stem = _file_stem(str(asset.get("name", ""))) or "picture"
        name, n = f"{stem}{suffix}", 2
        while name.lower() in taken:
            name, n = f"{stem}-{n}{suffix}", n + 1
        taken.add(name.lower())
        named.append((asset, f"brand/{folder}/{name}"))
    return named


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


def _summary(system: dict[str, Any]) -> str:
    typography = system["typography"]
    return (
        f"{len(system['colors'])} colors, {len(typography['fonts'])} fonts, "
        f"{len(typography['styles'])} text styles, {len(system['spacing'])} spacing and "
        f"{len(system['radius'])} corner radius values"
    )


def build_design_system_tools(state_dir: str | Path) -> list[Callable[..., Any]]:
    """The tool that saves a design system to the person's library. Deferred like the other
    non-core tools, so the fixed tool list (0001) is unchanged."""
    store = DesignSystemStore(state_dir)

    def save_design_system(
        name: str | None = None,
        overview: str | None = None,
        colors: list[dict[str, str]] | None = None,
        fonts: list[str] | None = None,
        text_styles: list[dict[str, Any]] | None = None,
        spacing: list[dict[str, str]] | None = None,
        radius: list[dict[str, str]] | None = None,
        system_id: str | None = None,
    ) -> dict[str, str]:
        """Save a design system to the user's library, where it shows on the Artifacts page and
        can be chosen for a new presentation. Without system_id it makes a new system (name is
        required) that starts from a neutral palette and six text styles; with the id of an
        existing system it changes only the fields you pass. A list you pass replaces the whole
        list. A value the library cannot accept comes back as an error to repair.

        Args:
            name: the system's name, up to 80 characters.
            overview: free text the model reads when it builds with the system: the brand, tone,
                and how the parts are meant to be used.
            colors: rows of {"name", "value", "note"}; value is #RRGGBB, note says what it is for.
            fonts: installed font family names.
            text_styles: rows of {"id", "name", "size", "weight", "line_height",
                "letter_spacing"}; size in px on a 1920 px wide slide, weight 100 to 900, line
                height as a multiple of size, letter spacing in px. A deck uses the ids
                heading-1, heading-3, lead, eyebrow, body and caption.
            spacing: rows of {"name", "value"}, for example {"name": "Margin", "value": "96px"}.
            radius: rows of {"name", "value"}, for example {"name": "Card", "value": "16px"}.
            system_id: the id returned when it was saved, to change that system.
        """
        if system_id is None:
            if not name:
                raise DesignSystemError("a new system needs a name")
            current: dict[str, Any] | None = store.create(name)
        else:
            current = store.get(system_id)
            if current is None:
                raise DesignSystemError("there is no design system with that id")
        assert current is not None
        typography = current["typography"]
        given = {
            "name": name,
            "overview": overview,
            "colors": colors,
            "spacing": spacing,
            "radius": radius,
        }
        data = {
            **{key: value for key, value in current.items() if key != "id"},
            **{key: value for key, value in given.items() if value is not None},
            "typography": {
                "fonts": typography["fonts"] if fonts is None else fonts,
                "styles": typography["styles"] if text_styles is None else text_styles,
            },
        }
        try:
            saved = store.update(current["id"], data)
        except DesignSystemError:
            if system_id is None:
                store.delete(current["id"])  # a half-made system must not stay in the library
            raise
        assert saved is not None
        return {"id": saved["id"], "name": saved["name"], "summary": _summary(saved)}

    return [tool_metadata(save_design_system, risk_category="WRITE_LOCAL", category="documents")]
