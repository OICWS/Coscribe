"""Icons a page names instead of drawing: `<use data-icon="ship" x y width height stroke>`
becomes the icon's paths, so the model writes one line where an icon would cost it dozens of
coordinates, and every icon in a deck shares one line weight and look.

The set is a chosen part of Tabler Icons (outline, 24 x 24 grid, 2 px stroke; MIT,
`ICONS_NOTICE.md`), kept as one file so it adds one small file to the install.
"""

from __future__ import annotations

import difflib
import json
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

_SVG_NS = "http://www.w3.org/2000/svg"
_GRID = 24.0
_DEFAULT_INK = "#1F2937"


@cache
def icons() -> dict[str, dict[str, object]]:
    """Name -> {"tags", "body"}: the icon's elements on its 24 px grid."""
    data = json.loads(Path(__file__).with_name("icons.json").read_text(encoding="utf-8"))
    return dict(data)


def expand_icons(root: ET.Element) -> list[str]:
    """Replace every `<use data-icon>` under `root` in place; one error per unknown name."""
    errors = []
    for parent in list(root.iter()):
        for index, child in enumerate(list(parent)):
            if child.tag != f"{{{_SVG_NS}}}use" or child.get("data-icon") is None:
                continue
            name = str(child.get("data-icon")).removeprefix("tabler-outline/")
            icon = icons().get(name)
            if icon is None:
                near = difflib.get_close_matches(name, icons(), n=4, cutoff=0.5)
                hint = f"; near: {', '.join(near)}" if near else ""
                errors.append(f'no icon named "{name}"{hint} (the list is in icons.md)')
                parent.remove(child)
                continue
            parent.remove(child)
            parent.insert(index, _drawn(child, str(icon["body"])))
    return errors


def _drawn(use: ET.Element, body: str) -> ET.Element:
    x, y = float(use.get("x", 0)), float(use.get("y", 0))
    size = float(use.get("width", use.get("height", _GRID)))
    ink = use.get("stroke") or use.get("fill") or use.get("color") or _DEFAULT_INK
    # A group may only translate (the compiler's page language), so the scale sits on an inner
    # group, where it also scales the stroke the way the icon was drawn.
    outer = ET.Element(f"{{{_SVG_NS}}}g", {"transform": f"translate({x:g} {y:g})"})
    if use.get("id"):
        outer.set("id", str(use.get("id")))
    inner = ET.SubElement(
        outer,
        f"{{{_SVG_NS}}}g",
        {
            "transform": f"scale({size / _GRID:g})",
            "fill": "none",
            "stroke": ink,
            "stroke-width": use.get("stroke-width", "2"),
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
    )
    for element in ET.fromstring(f'<g xmlns="{_SVG_NS}">{body}</g>'):
        inner.append(element)
    return outer
