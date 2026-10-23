"""A deck's design system (decision 0017): the palette, fonts and named text styles the Slides
panel offers, kept in `design-system.json` in the deck's pages folder. A section never refers to
it; choosing a style writes the values into the element and marks it `data-text-style`.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from ...._file_locks import file_lock, replace_with_retry
from .design_check import COLOUR, DESIGN_SYSTEM, FONT
from .section_format import DEFAULT_FONT
from .view import NotBuiltFromPages, pages_folder

_PALETTE_SIZE = 10
_FALLBACK_PALETTE = ["#1F2937", "#4B5563", "#9CA3AF", "#E5E7EB", "#FFFFFF", "#2563EB"]
# The text styles every deck starts with: id, name, size (px on the 1920 canvas), weight, line
# height, letter spacing (px).
_STYLES = [
    ("heading-1", "Heading 1", 144, 700, 1.1, 0),
    ("heading-3", "Heading 3", 44, 700, 1.2, 0),
    ("lead", "Lead", 44, 400, 1.3, 0),
    ("eyebrow", "Eyebrow", 24, 700, 1.2, 3),
    ("body", "Body", 32, 400, 1.4, 0),
    ("caption", "Caption", 24, 400, 1.3, 0),
]


def design_system(deck: Path, seed: dict[str, Any] | None = None) -> dict[str, Any]:
    """The deck's design system: `name`, `palette` (#RRGGBB, most used first), `fonts` and
    `styles` (each `id`, `name`, `size`, `weight`, `line_height`, `letter_spacing`). It is made
    from the deck's own pages and saved the first time it is read; a file the user or the app
    changed is kept. A damaged file is replaced in memory by the default, not overwritten. A
    `seed` (a library system the conversation started with, already in this shape) takes the
    place of the default the first time."""
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    path = folder / DESIGN_SYSTEM
    with file_lock(path):
        found = _load(path)
        if found is not None:
            return found
        made = seed if seed is not None and _load_dict(seed) else _default(folder, deck.stem)
        if not path.exists():
            tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
            tmp.write_text(json.dumps(made, ensure_ascii=False, indent=2), encoding="utf-8")
            replace_with_retry(tmp, path)
        return made


def _load(path: Path) -> dict[str, Any] | None:
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return _load_dict(data)


def _load_dict(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    styles = data.get("styles")
    if not (isinstance(data.get("palette"), list) and isinstance(data.get("fonts"), list)):
        return None
    if not isinstance(styles, list):
        return None
    if not all(isinstance(s, dict) and isinstance(s.get("id"), str) for s in styles):
        return None
    return {str(k): v for k, v in data.items()}


def _default(folder: Path, name: str) -> dict[str, Any]:
    texts = [p.read_text(encoding="utf-8", errors="replace") for p in sorted(folder.glob("*.html"))]
    texts += [p.read_text(encoding="utf-8", errors="replace") for p in sorted(folder.glob("*.svg"))]
    counts = Counter(c.upper() for text in texts for c in COLOUR.findall(text))
    palette = [colour for colour, _ in counts.most_common(_PALETTE_SIZE)] or _FALLBACK_PALETTE
    fonts = Counter(f.strip().strip("'\"") for text in texts for f in FONT.findall(text))
    return {
        "name": name,
        "palette": palette,
        "fonts": [f for f, _ in fonts.most_common(3)] or [DEFAULT_FONT],
        "styles": [
            {"id": i, "name": n, "size": s, "weight": w, "line_height": h, "letter_spacing": ls}
            for i, n, s, w, h, ls in _STYLES
        ],
    }
