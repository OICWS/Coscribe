"""What a page uses that the deck's design system does not have (decision 0020: the system guides
the model, it does not forbid): colors, fonts and named text styles, as warnings on the page so
the model repairs them or says why. Only a deck that began from a system of the person's library
is checked; a deck's own system is made from its pages.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

DESIGN_SYSTEM = "design-system.json"
COLOUR = re.compile(r"#[0-9a-fA-F]{6}\b")
FONT = re.compile(r"font-family(?::\s*|=\")([^;\"]+)")
# Colors a page may always use: text on a dark fill, a plain background.
_NEUTRAL = {"#FFFFFF", "#000000"}
# Pages carry tints and rounding of a palette color; this far (in RGB steps) counts as the same.
_NEAR = 16.0
_GENERIC_FONTS = {"sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui", "inherit"}
_STYLE = re.compile(r"""data-text-style=["']([^"']+)["']""")
# A page with many strays gets the first few named and a count.
_LISTED = 4


def library_system(folder: Path) -> dict[str, Any] | None:
    """The system a deck started from, when it came from the person's library (it names its
    `source`); None for a deck's own, which is made from its pages and so cannot differ from them,
    and for a missing or damaged file. Reads only."""
    try:
        data = json.loads((folder / DESIGN_SYSTEM).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    ok = isinstance(data, dict) and data.get("source")
    shaped = ok and all(isinstance(data.get(k), list) for k in ("palette", "fonts", "styles"))
    return data if shaped else None


def off_system(system: dict[str, Any], pages: Sequence[tuple[str, str]]) -> dict[str, list[str]]:
    """Warnings per page name, for the pages `(name, source text)` that use something the
    `system` (in the deck's `design-system.json` shape) does not have."""
    palette = [p for c in system.get("palette", []) if isinstance(c, str) and (p := _rgb(c))]
    fonts = {str(f).strip().lower() for f in system.get("fonts", [])}
    styles = {s.get("id") for s in system.get("styles", []) if isinstance(s, dict)}
    name = system.get("name", "")
    found: dict[str, list[str]] = {}
    for page, text in pages:
        warnings = []
        strays = _unlisted(
            [c.upper() for c in COLOUR.findall(text)], lambda c: _in_palette(c, palette)
        )
        if strays and palette:
            warnings.append(
                _listed(strays, lambda c: f"{c} (nearest {_nearest(c, system['palette'])})")
                + f" not in the design system {name!r}'s colors"
            )
        if fonts:
            wrong = _unlisted(
                [f.split(",")[0].strip().strip("'\"") for f in FONT.findall(text)],
                lambda f: f.lower() in fonts or f.lower() in _GENERIC_FONTS,
            )
            if wrong:
                warnings.append(
                    _listed(wrong, repr)
                    + f" not among the design system's fonts ({', '.join(sorted(fonts))})"
                )
        unknown = _unlisted(_STYLE.findall(text), lambda s: s in styles)
        if unknown:
            warnings.append(_listed(unknown, repr) + " not a text style of the design system")
        if warnings:
            found[page] = [f"off the design system: {w}" for w in warnings]
    return found


def _unlisted(values: list[str], known: Any) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        if value and not known(value):
            seen.setdefault(value, None)
    return list(seen)


def _listed(values: list[str], show: Any) -> str:
    shown = ", ".join(show(v) for v in values[:_LISTED])
    return shown + (f" and {len(values) - _LISTED} more" if len(values) > _LISTED else "")


def _rgb(colour: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})", colour.strip())
    return (int(match[1], 16), int(match[2], 16), int(match[3], 16)) if match else None


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return math.dist(a, b)


def _in_palette(colour: str, palette: list[tuple[int, int, int]]) -> bool:
    rgb = _rgb(colour)
    return (
        colour in _NEUTRAL
        or rgb is None
        or not palette
        or any(_distance(rgb, p) <= _NEAR for p in palette)
    )


def _nearest(colour: str, palette: list[Any]) -> str:
    rgb = _rgb(colour)
    options = [(str(c).upper(), p) for c in palette if (p := _rgb(str(c))) is not None]
    if rgb is None or not options:
        return ""
    return min(options, key=lambda option: _distance(rgb, option[1]))[0]
