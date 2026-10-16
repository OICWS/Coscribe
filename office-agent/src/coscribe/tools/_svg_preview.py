"""A deck page previewed from the SVG it was compiled from (decision 0012), with resvg: no office
program is needed. A native chart or table is drawn by PowerPoint from its JSON, not from the
SVG, so here it is a labelled box of the size it will have."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_SVG = "http://www.w3.org/2000/svg"
PREVIEW_WIDTH = 1280


def _label(kind: str, data: dict[str, Any]) -> str:
    if kind == "table":
        columns, rows = data.get("columns") or [], data.get("rows") or []
        return f"Table: {len(columns)} columns, {len(rows)} rows"
    names = [str(s.get("name", "")) for s in data.get("series") or [] if isinstance(s, dict)]
    title = data.get("title") or ", ".join(n for n in names if n)
    return f"{data.get('type', 'chart').capitalize()} chart" + (f": {title}" if title else "")


def _placeholder(group: ET.Element, kind: str) -> None:
    """Replaces the group's content with a box at the frame its JSON gives."""
    metadata = group.find(f"{{{_SVG}}}metadata")
    try:
        data: Any = json.loads(metadata.text or "") if metadata is not None else {}
        x, y, w, h = (float(data[k]) for k in ("x", "y", "width", "height"))
    except (ValueError, KeyError, TypeError):
        return
    for child in list(group):
        group.remove(child)
    box = {"x": x, "y": y, "width": w, "height": h}
    ET.SubElement(
        group,
        f"{{{_SVG}}}rect",
        {
            **{k: str(v) for k, v in box.items()},
            "fill": "#F1F5F9",
            "stroke": "#94A3B8",
            "stroke-dasharray": "8 6",
            "stroke-width": "2",
        },
    )
    lines = [
        (_label(kind, data), 22, "#475569"),
        ("PowerPoint draws it from its data", 16, "#64748B"),
    ]
    for offset, (words, size, color) in zip((0, 32), lines, strict=True):
        line = ET.SubElement(
            group,
            f"{{{_SVG}}}text",
            {
                "x": str(x + w / 2),
                "y": str(y + h / 2 + offset),
                "fill": color,
                "font-family": "sans-serif",
                "font-size": str(size),
                "text-anchor": "middle",
                "dominant-baseline": "middle",
            },
        )
        line.text = words


def page_svg(svg_path: Path) -> str:
    """The page's SVG with each native chart and table as its placeholder."""
    from .office.pptx.engine.native import native_kind

    ET.register_namespace("", _SVG)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    for group in root.iter(f"{{{_SVG}}}g"):
        kind = native_kind(group)
        if kind:
            _placeholder(group, kind)
    return ET.tostring(root, encoding="unicode")


def render_page(svg_path: Path, target: Path, width: int = PREVIEW_WIDTH) -> None:
    """Writes the page as a PNG. Raises ValueError (resvg's own error) or ET.ParseError when the
    page cannot be drawn."""
    import resvg_py

    png = resvg_py.svg_to_bytes(
        svg_string=page_svg(svg_path),
        width=width,
        resources_dir=str(svg_path.parent),
        background="#ffffff",
    )
    target.write_bytes(bytes(png))
