"""The theme a document takes from a design system of the person's library (decision 0024): the
accent colour and the font. The text sizes of a system are pixels on a slide, so they do not carry
over; the document keeps its own."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...design_systems import DesignSystemStore
from ._style import ACCENT
from .spec import SpecError

_ACCENT_NAMES = re.compile(r"accent|primary|brand", re.IGNORECASE)
_COLOUR = re.compile(r"#?([0-9A-Fa-f]{6})")


@dataclass(frozen=True)
class Theme:
    accent: str = ACCENT
    font: str | None = None


def theme_of(system: dict[str, Any]) -> Theme:
    """The accent is the colour named accent, primary or brand, else the first colour that is not
    near white; the font is the system's first."""
    colours = [
        (str(row.get("name", "")), m.group(1).upper())
        for row in system.get("colors", [])
        if isinstance(row, dict) and (m := _COLOUR.fullmatch(str(row.get("value", ""))))
    ]
    named = [value for name, value in colours if _ACCENT_NAMES.search(name)]
    dark = [value for _, value in colours if not _near_white(value)]
    fonts = system.get("typography", {}).get("fonts", [])
    return Theme(
        accent=(named or dark or [ACCENT])[0],
        font=str(fonts[0]) if fonts else None,
    )


def _near_white(hex6: str) -> bool:
    return all(int(hex6[i : i + 2], 16) > 0xE0 for i in (0, 2, 4))


def load_theme(name: str, state_dir: Path | None) -> Theme:
    """The theme of the library system called `name`; SpecError names the ones there are."""
    store = DesignSystemStore(state_dir) if state_dir is not None else None
    listed = store.list_systems() if store is not None else []
    for entry in listed:
        if entry["name"].casefold() == name.casefold() and store is not None:
            system = store.get(entry["id"])
            if system is not None:
                return theme_of(system)
    known = ", ".join(entry["name"] for entry in listed) or "none yet"
    raise SpecError(f"No design system called {name!r} in the library (there are: {known})")
