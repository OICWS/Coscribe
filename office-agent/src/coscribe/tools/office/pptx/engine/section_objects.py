"""A section's tables, charts and icons, handed to the SVG pages' own converters.

A `<table>` and an `<x-chart>` become the JSON groups the pages use for native PowerPoint tables
and charts (`native.py`), so they come out as objects whose data the user edits in PowerPoint; an
`<x-icon>` becomes the pages' `<use data-icon>`. The native converters place a frame by the JSON's
own box and size its text by the JSON's px, not by the conversion's scale, so both are converted
from the 1920-wide canvas here.
"""

from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree as ET

from .compiler import SVG_NS
from .section_format import (
    SectionError,
    Style,
    colour,
    label,
    local,
    read_cell_style,
    read_style,
)

_ALIGN = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}
_ROW_GROUPS = {"thead", "tbody", "tfoot"}
_CELL_INLINE = {"b", "strong", "i", "em", "span", "br"}
_BOX_KEYS = ("x", "y", "width", "height")


def chart(elem: ET.Element, style: Style, scale: float) -> ET.Element:
    try:
        spec = json.loads(elem.text or "")
    except ValueError as e:
        raise SectionError(f"{label(elem)} holds the chart's JSON: {e}") from None
    if not isinstance(spec, dict) or len(elem):
        raise SectionError(f"{label(elem)} holds one JSON object and nothing else")
    if any(key in spec for key in _BOX_KEYS):
        raise SectionError(f"{label(elem)}: its box is in its style, not in the JSON")
    _place(spec, style, scale)
    if "font_size" in spec:
        spec["font_size"] = _scaled(spec["font_size"], scale, label(elem))
    return _native(elem, "chart", spec)


def table(elem: ET.Element, style: Style, scale: float) -> ET.Element:
    rows = _rows(elem)
    grid = _grid(elem, rows)
    header_rows = 0
    while header_rows < len(rows) and all(local(c) == "th" for c in rows[header_rows]):
        header_rows += 1
    spec: dict[str, Any] = {
        "schema": "ppt-master.semantic-table.v2",
        "rows": grid,
        "header_rows": header_rows,
        "style": _table_style(style, scale, rows[0] if header_rows else []),
    }
    widths = _column_widths(elem, scale)
    if widths:
        spec["column_widths"] = widths
    _place(spec, style, scale)
    return _native(elem, "table", spec)


def icon(elem: ET.Element, style: Style) -> ET.Element:
    x, y, w, h = style.box()
    attrs = {
        "data-icon": elem.get("data-icon", ""),
        "x": f"{x:g}",
        "y": f"{y:g}",
        "width": f"{min(w, h):g}",
        "height": f"{min(w, h):g}",
        "stroke": f"#{style.colour('color', '1F2937')}",
    }
    if elem.get("id"):
        attrs["id"] = elem.get("id", "")
    # Icons are expanded in place before conversion, so the compiler holds the holder, not the
    # `<use>` that gets replaced.
    holder = ET.Element(f"{{{SVG_NS}}}g")
    ET.SubElement(holder, f"{{{SVG_NS}}}use", attrs)
    return holder


def _native(elem: ET.Element, kind: str, spec: dict[str, Any]) -> ET.Element:
    group = ET.Element(f"{{{SVG_NS}}}g", {"data-pptx-replace-with": kind})
    if elem.get("id"):
        group.set("id", elem.get("id", ""))
    metadata = ET.SubElement(group, f"{{{SVG_NS}}}metadata", {"type": "application/json"})
    metadata.text = json.dumps(spec, ensure_ascii=False)
    return group


def _place(spec: dict[str, Any], style: Style, scale: float) -> None:
    for key, value in zip(_BOX_KEYS, style.box(), strict=True):
        spec[key] = value * scale


def _scaled(value: Any, scale: float, where: str) -> float:
    if not isinstance(value, int | float):
        raise SectionError(f"{where}: font_size is a number of px")
    return round(value * scale, 2)


def _rows(elem: ET.Element) -> list[list[ET.Element]]:
    rows: list[list[ET.Element]] = []
    for child in elem:
        tag = local(child)
        if tag in _ROW_GROUPS | {"colgroup"} and child.attrib:
            raise SectionError(f"{label(elem)}: <{tag}> takes no attributes")
        if tag == "colgroup":
            continue
        trs = list(child) if tag in _ROW_GROUPS else [child]
        for tr in trs:
            if local(tr) != "tr" or tr.attrib:
                raise SectionError(f"{label(elem)} holds rows (<tr>) of <th> and <td> cells")
            cells = list(tr)
            if not cells or any(local(c) not in {"th", "td"} for c in cells):
                raise SectionError(f"{label(elem)}: a row holds <th> and <td> cells only")
            rows.append(cells)
    if not rows:
        raise SectionError(f"{label(elem)} has no rows")
    return rows


def _grid(elem: ET.Element, rows: list[list[ET.Element]]) -> list[list[Any]]:
    """HTML leaves out the cells a merged cell covers; the table JSON wants them, blank."""
    taken: set[tuple[int, int]] = set()
    grid: list[list[Any]] = []
    for r, cells in enumerate(rows):
        row: list[Any] = []
        c = 0
        for cell in cells:
            while (r, c) in taken:
                row.append("")
                c += 1
            payload, cols, span_rows = _cell(cell, elem)
            row.append(payload)
            for dr in range(span_rows):
                for dc in range(cols):
                    if dr or dc:
                        taken.add((r + dr, c + dc))
            c += 1
            row.extend("" for _ in range(cols - 1))
            c += cols - 1
        while (r, c) in taken:
            row.append("")
            c += 1
        grid.append(row)
    if len({len(row) for row in grid}) != 1:
        raise SectionError(f"{label(elem)}: every row must have the same number of columns")
    return grid


def _cell(cell: ET.Element, table_elem: ET.Element) -> tuple[Any, int, int]:
    if cell.attrib.keys() - {"style", "colspan", "rowspan"}:
        raise SectionError(f"{label(table_elem)}: a cell takes style, colspan and rowspan only")
    style = read_cell_style(cell)
    text = _cell_text(cell, table_elem)
    payload: dict[str, Any] = {"text": text}
    if "text-align" in style.values:
        align = style.values["text-align"].strip().lower()
        if align not in _ALIGN:
            raise SectionError(f"{label(table_elem)}: text-align is one of {', '.join(_ALIGN)}")
        payload["align"] = _ALIGN[align]
    if "color" in style.values:
        payload["color"] = f"#{style.colour('color')}"
    if "background" in style.values:
        payload["fill"] = f"#{style.colour('background')}"
    if "font-weight" in style.values:
        weight = style.values["font-weight"].strip().lower()
        payload["bold"] = weight == "bold" or (weight.isdigit() and int(weight) >= 600)
    cols, rows = _span(cell, "colspan", table_elem), _span(cell, "rowspan", table_elem)
    if cols > 1:
        payload["col_span"] = cols
    if rows > 1:
        payload["row_span"] = rows
    return (payload if len(payload) > 1 else text), cols, rows


def _cell_text(cell: ET.Element, table_elem: ET.Element) -> str:
    parts = [cell.text or ""]
    for child in cell:
        for node in child.iter():
            _check_inline(node, table_elem)
        parts.append("\n" if local(child) == "br" else "".join(child.itertext()))
        parts.append(child.tail or "")
    lines = "".join(parts).split("\n")
    return "\n".join(" ".join(line.split()) for line in lines)


def _check_inline(node: ET.Element, table_elem: ET.Element) -> None:
    """What a cell may hold, at any depth: the app draws the cell as written."""
    tag = local(node)
    if tag not in _CELL_INLINE:
        raise SectionError(f"{label(table_elem)}: {label(node)} cannot sit in a cell")
    if tag == "span" and set(node.attrib) <= {"style"}:
        read_style(node, "span")
    elif node.attrib:
        raise SectionError(f"{label(table_elem)}: <{tag}> in a cell takes no attributes")


def _span(cell: ET.Element, name: str, table_elem: ET.Element) -> int:
    raw = cell.get(name, "1")
    if not raw.isdigit() or int(raw) < 1:
        raise SectionError(f"{label(table_elem)}: {name} is a whole number, got {raw!r}")
    return int(raw)


def _table_style(style: Style, scale: float, header: list[ET.Element]) -> dict[str, Any]:
    out: dict[str, Any] = {"band_row": False}
    out["font_size"] = round(style.px("font-size", 24.0) * scale, 2)
    if "font-family" in style.values:
        out["font_family"] = style.values["font-family"]
    if "color" in style.values:
        out["body_text"] = f"#{style.colour('color')}"
    if "background" in style.values:
        out["body_fill"] = f"#{style.colour('background')}"
    if "border-color" in style.values:
        out["border_color"] = f"#{colour(style.values['border-color'], style.label)}"
    first = read_cell_style(header[0]) if header else None
    if first is not None and "background" in first.values:
        out["header_fill"] = f"#{first.colour('background')}"
    if first is not None and "color" in first.values:
        out["header_text"] = f"#{first.colour('color')}"
    return out


def _column_widths(elem: ET.Element, scale: float) -> list[float]:
    group = next((c for c in elem if local(c) == "colgroup"), None)
    if group is None:
        return []
    widths = []
    for col in group:
        if local(col) != "col" or col.attrib.keys() - {"style"} or len(col):
            raise SectionError(f'{label(elem)}: a <colgroup> holds <col style="width:Npx"/>')
        widths.append(round(read_cell_style(col).px("width") * scale, 2))
    return widths
