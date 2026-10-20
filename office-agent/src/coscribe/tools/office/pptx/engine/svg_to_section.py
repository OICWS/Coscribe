"""An SVG page turned into a slide section with the same content (decision 0016).

New slides are SVG pages; a slide becomes a section when the user first edits it, so nothing on it
may move or change in the conversion. Text is the part the user edits, so it becomes text boxes,
and each is placed where the pages' emitter puts it in PowerPoint: the text is converted by that
emitter and its box, runs and spacing are read back. Everything else stays SVG, one `<svg>` element
per top-level shape or group cropped to its bounds, so the same emitter draws it as before.
Anything the section language cannot say exactly (a rotated text, a gradient on text, a table
with uneven rows) stays SVG too, and the conversion says so.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from lxml import etree

from ...._native_svg.svg_to_pptx import geometry_properties, tspan_flattener
from ...._native_svg.svg_to_pptx.drawingml import utils
from ...._native_svg.svg_to_pptx.drawingml.context import ConvertContext
from . import native
from .compiler import (
    EMU_PER_PX as PAGE_EMU_PER_PX,
)
from .compiler import (
    NSDECL,
    SVG_NS,
    PageReport,
    convert_element,
)
from .section_format import CANVAS, SectionError
from .text_box import EMU_PER_PX

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_ALIGN = {"l": "left", "ctr": "center", "r": "right", "just": "justify"}
_FIT = {"xMidYMid slice": "cover", "xMidYMid meet": "contain", "none": "fill", "": "contain"}
_NON_VISUAL = {"defs", "title", "desc", "metadata", "style"}
_HEIGHT_ROOM = 1.25
# Strokes and shadows reach past a shape's geometric bounds; a cropped drawing keeps this margin.
_DRAWING_MARGIN = 6.0
_TABLE_KEYS = {
    "schema",
    "columns",
    "rows",
    "header_rows",
    "style",
    "column_widths",
    "x",
    "y",
    "width",
    "height",
    "row_heights",
}
_TABLE_STYLE_KEYS = {
    "font_size",
    "font_family",
    "body_text",
    "body_fill",
    "header_fill",
    "header_text",
    "band_fill",
    "band_row",
    "border_color",
}
_CELL_KEYS = {"text", "align", "color", "fill", "bold", "col_span", "row_span"}
# The attributes of a plain shape the section language says exactly; any other (a filter, a
# gradient, a dash, a transform) keeps the shape a drawing.
_PAINT_ATTRS = {"id", "fill", "stroke", "stroke-width", "opacity"}
_SHAPE_ATTRS = {
    "rect": _PAINT_ATTRS | {"x", "y", "width", "height", "rx", "ry"},
    "ellipse": _PAINT_ATTRS | {"cx", "cy", "rx", "ry"},
    "circle": _PAINT_ATTRS | {"cx", "cy", "r"},
    "line": _PAINT_ATTRS | {"x1", "y1", "x2", "y2"},
}
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")
_TRANSLATE = re.compile(r"\s*translate\(\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+))?\s*\)\s*")


class _Unsupported(Exception):
    """This element cannot be said exactly in the section language; it stays SVG."""


def convert_page(svg_text: str) -> tuple[str, list[str]]:
    """The section that compiles to the same slide as the SVG page `svg_text`, and the elements
    kept as drawings that a fuller conversion would have made editable."""
    root = ET.fromstring(svg_text)
    if root.get("data-template-slide") or root.get("data-layout"):
        raise SectionError("a slide built on a template stays an SVG page")
    scale = _scale(root)
    page = _prepared(root)
    defs = [c for c in page if _local(c) == "defs"]
    ctx = _context(page, scale)
    out = _Writer(scale, ctx)
    background = _background(page)
    for child in list(page):
        out.element(child)
    attrs = f' style="background:#{background}"' if background else ""
    parts = [f"<section{attrs}>"]
    if defs:
        parts.append(_defs_holder(defs))
    parts += out.parts
    notes = _notes(page)
    if notes:
        parts.append(f"<aside>{escape(chr(10).join(notes))}</aside>")
    parts.append("</section>")
    return "\n".join(parts), out.kept


def _scale(root: ET.Element) -> float:
    view = [float(v) for v in (root.get("viewBox") or "").replace(",", " ").split()]
    if len(view) != 4 or view[2] <= 0:
        raise SectionError('the page needs viewBox="0 0 W H"')
    scale = CANVAS[0] / view[2]
    if abs(view[3] * scale - CANVAS[1]) > 0.5:
        raise SectionError("only a 16:9 page converts to a section")
    return scale


def _prepared(root: ET.Element) -> ET.Element:
    """The page as the compiler sees it: inline geometry made explicit and positioned lines
    merged into paragraphs, so a text converts to the box the compiler would write."""
    page = copy.deepcopy(root)
    geometry_properties.materialize_inline_geometry_properties(page)
    tspan_flattener.flatten_positional_tspans(
        ET.ElementTree(page), merge_paragraphs=True, preserve_line_breaks=True
    )
    return page


def _context(page: ET.Element, scale: float) -> ConvertContext:
    defs, _duplicates = utils.project_definition_index(page)
    return ConvertContext(
        defs=defs,
        inherited_styles=utils._extract_inheritable_styles(page),
        viewport_width=CANVAS[0] / scale,
        viewport_height=CANVAS[1] / scale,
        rel_id_counter=1000,
    )


class _Writer:
    """Writes the section's elements in the page's drawing order."""

    def __init__(self, scale: float, ctx: ConvertContext) -> None:
        self.scale, self.ctx = scale, ctx
        self.parts: list[str] = []
        self.kept: list[str] = []

    def element(self, elem: ET.Element, ctx: ConvertContext | None = None) -> None:
        tag = _local(elem)
        if tag in _NON_VISUAL:
            return
        ctx = ctx or self.ctx
        try:
            self.parts.append(self._editable(elem, tag, ctx))
            return
        except _Unsupported as why:
            if str(why):
                self.kept.append(f"{_label(elem)}: {why}")
        if tag == "g" and not native.native_kind(elem):
            if any(_local(d) == "text" for d in elem.iter()):
                self._split_group(elem, ctx)
                return
            shapes = _group_shapes(elem, self.scale)
            if shapes is not None:
                self.parts.extend(shapes)
                return
        self._drawing(elem)

    def _editable(self, elem: ET.Element, tag: str, ctx: ConvertContext) -> str:
        if tag == "text":
            return _text(elem, ctx, self.scale)
        if tag == "image":
            return _image(elem, self.scale)
        if tag in _SHAPE_ATTRS:
            return _shape(elem, self.scale)
        if tag == "use" and elem.get("data-icon"):
            return _icon(elem, self.scale)
        if tag == "g" and native.native_kind(elem) == "chart":
            return _chart(elem, self.scale)
        if tag == "g" and native.native_kind(elem) == "table":
            return _table(elem, self.scale)
        raise _Unsupported("")

    def _split_group(self, group: ET.Element, ctx: ConvertContext) -> None:
        """A card: its shapes stay one drawing, its texts become text boxes over it. When one
        of its texts cannot be said exactly, the whole group stays a drawing."""
        try:
            boxes = [_text(t, tctx, self.scale) for t, tctx in _texts_in(group, ctx)]
        except _Unsupported as why:
            self.kept.append(f"{_label(group)}: {why}")
            self._drawing(group)
            return
        flat = _group_shapes(group, self.scale)
        if flat is not None:
            self.parts.extend(flat)
            self.parts.extend(boxes)
            return
        shapes = copy.deepcopy(group)
        _remove_texts(shapes)
        if any(_local(c) not in _NON_VISUAL for c in shapes.iter() if c is not shapes):
            self._drawing(shapes)
        self.parts.extend(boxes)

    def _drawing(self, elem: ET.Element) -> None:
        box = _bounds(elem, self.ctx)
        if box is None:
            return
        x, y, w, h = box
        m = _DRAWING_MARGIN
        view = (x - m, y - m, w + 2 * m, h + 2 * m)
        s = self.scale
        style = (
            f"left:{view[0] * s:g}px;top:{view[1] * s:g}px;"
            f"width:{view[2] * s:g}px;height:{view[3] * s:g}px"
        )
        ident = f' id="{_attr(elem.get("id", ""))}"' if elem.get("id") else ""
        body = _svg_markup(elem)
        self.parts.append(
            f'<svg xmlns="{SVG_NS}"{ident} viewBox="{" ".join(f"{v:g}" for v in view)}" '
            f'style="{style}">{body}</svg>'
        )


def _text(elem: ET.Element, ctx: ConvertContext, scale: float) -> str:
    result = convert_element(elem, ctx, PageReport("convert"))
    if result is None:
        raise _Unsupported("the compiler draws nothing for it")
    shape = next(iter(etree.fromstring(f"<w {NSDECL}>{result.xml}</w>")))
    xfrm = shape.find(f".//{_A}xfrm")
    if xfrm is None or xfrm.get("rot") or xfrm.get("flipH") or xfrm.get("flipV"):
        raise _Unsupported("rotated or flipped text")
    off, ext = xfrm.find(f"{_A}off"), xfrm.find(f"{_A}ext")
    x, y = int(off.get("x")) / EMU_PER_PX, int(off.get("y")) / EMU_PER_PX
    w, h = int(ext.get("cx")) / EMU_PER_PX, int(ext.get("cy")) / EMU_PER_PX
    paragraphs = shape.findall(f".//{_A}p")
    runs = [r for p in paragraphs for r in p if etree.QName(r).localname in {"r", "br"}]
    first = next((r for r in runs if etree.QName(r).localname == "r"), None)
    if first is None:
        raise _Unsupported("no text")
    base = _run_style(first.find(f"{_A}rPr"))
    align = paragraphs[0].find(f"{_A}pPr")
    algn = align.get("algn", "l") if align is not None else "l"
    style = {
        "left": f"{x:g}px",
        "top": f"{y:g}px",
        "width": f"{w:g}px",
        # Room for our line measure, which is a little more cautious than the emitter's. The
        # compiled box is drawn at the text's own height, so the room changes nothing visible.
        "height": f"{h * _HEIGHT_ROOM:g}px",
        "font-size": f"{base['size']:g}px",
        "font-family": base["family"],
        "color": base["color"],
        "text-align": _ALIGN.get(algn, "left"),
        "line-height": _line_height(paragraphs[0], base["size"]),
        # The page's lines are where its author put them; the box wraps once the user edits it.
        "white-space": "nowrap",
    }
    if base["bold"]:
        style["font-weight"] = "bold"
    if base["italic"]:
        style["font-style"] = "italic"
    if base["tracking"]:
        style["letter-spacing"] = f"{base['tracking']:g}px"
    content = "<br/>".join(_paragraph_markup(p, base) for p in paragraphs)
    ident = elem.get("id") or ""
    attr = f' id="{_attr(ident)}"' if ident else ""
    css = ";".join(f"{k}:{v}" for k, v in style.items())
    return f'<p{attr} style="{css}">{content}</p>'


def _run_style(rpr: Any) -> dict[str, Any]:
    if rpr is None:
        raise _Unsupported("a run without properties")
    fill = rpr.find(f"{_A}solidFill")
    colour = fill.find(f"{_A}srgbClr") if fill is not None else None
    if colour is None or len(colour) or rpr.find(f"{_A}gradFill") is not None:
        raise _Unsupported("text that is not one solid colour")
    latin = rpr.find(f"{_A}latin")
    ea = rpr.find(f"{_A}ea")
    faces = [f.get("typeface") for f in (ea, latin) if f is not None and f.get("typeface")]
    family = ", ".join(dict.fromkeys(faces)) or "Microsoft YaHei, Arial"
    return {
        "size": int(rpr.get("sz", "1800")) / 100 * 2,  # pt to the 1920 canvas's px
        "bold": rpr.get("b") == "1",
        "italic": rpr.get("i") == "1",
        "underline": rpr.get("u", "none") != "none",
        "tracking": int(rpr.get("spc", "0")) / 100 * 2,
        "color": f"#{colour.get('val').upper()}",
        "family": family,
    }


def _paragraph_markup(paragraph: Any, base: dict[str, Any]) -> str:
    out = []
    for node in paragraph:
        kind = etree.QName(node).localname
        if kind == "br":
            out.append("<br/>")
        elif kind == "r":
            text = escape(_kept_spaces("".join(t.text or "" for t in node.iter(f"{_A}t"))))
            out.append(_run_markup(text, _run_style(node.find(f"{_A}rPr")), base))
    return "".join(out)


def _kept_spaces(text: str) -> str:
    """Spaces HTML would collapse or drop (at a run's ends, or several in a row) as no-break
    spaces, which PowerPoint draws as wide as a space."""
    text = re.sub(r"  +", lambda m: "\u00a0" * len(m.group(0)), text)
    text = re.sub(r"^ +", lambda m: "\u00a0" * len(m.group(0)), text)
    return re.sub(r" +$", lambda m: "\u00a0" * len(m.group(0)), text)


def _run_markup(text: str, run: dict[str, Any], base: dict[str, Any]) -> str:
    css = []
    for key, prop, value in (
        ("family", "font-family", run["family"]),
        ("size", "font-size", f"{run['size']:g}px"),
        ("color", "color", run["color"]),
        ("tracking", "letter-spacing", f"{run['tracking']:g}px"),
    ):
        if run[key] != base[key]:
            css.append(f"{prop}:{value}")
    if run["bold"] != base["bold"]:
        css.append(f"font-weight:{'bold' if run['bold'] else 'normal'}")
    if run["italic"] != base["italic"]:
        css.append(f"font-style:{'italic' if run['italic'] else 'normal'}")
    if css:
        text = f'<span style="{";".join(css)}">{text}</span>'
    return f"<u>{text}</u>" if run["underline"] else text


def _line_height(paragraph: Any, size: float) -> str:
    """Exact spacing as a multiple of the size; the emitter writes none for a single line,
    which is the face's own spacing."""
    pts = paragraph.find(f"{_A}pPr/{_A}lnSpc/{_A}spcPts")
    if pts is None:
        if paragraph.find(f"{_A}pPr/{_A}lnSpc") is not None:
            raise _Unsupported("line spacing as a percentage")
        return "normal"
    return f"{int(pts.get('val')) / 100 * 2 / size:.4g}"


def _image(elem: ET.Element, scale: float) -> str:
    if any(elem.get(a) for a in ("transform", "clip-path", "opacity", "filter", "mask")):
        raise _Unsupported("a picture with a transform, clip, filter or opacity")
    fit = _FIT.get((elem.get("preserveAspectRatio") or "").strip())
    if fit is None:
        raise _Unsupported("a picture aligned other than in the middle")
    href = elem.get("href") or elem.get("{http://www.w3.org/1999/xlink}href") or ""
    if href.startswith("data:"):
        raise _Unsupported("an embedded picture")
    ident = f' id="{_attr(elem.get("id", ""))}"' if elem.get("id") else ""
    return f'<img{ident} src="{_attr(href)}" style="{_box(elem, scale)};object-fit:{fit}"/>'


def _number(elem: ET.Element, name: str, default: float | None = None) -> float:
    raw = elem.get(name)
    if raw is None:
        if default is None:
            raise _Unsupported("")
        return default
    try:
        return float(raw)
    except ValueError:
        raise _Unsupported("") from None


def _paint(elem: ET.Element, scale: float, *, fill: bool) -> str:
    """The style declarations that paint a plain shape, or _Unsupported for a paint the section
    language has no word for (a named colour, a gradient, a shape with neither fill nor line)."""
    declared = [
        ("fill", elem.get("fill", "#000000" if fill else "none")),
        ("stroke", elem.get("stroke", "none")),
    ]
    values = {}
    for name, raw in declared:
        raw = raw.strip()
        if raw != "none" and not _HEX.fullmatch(raw):
            raise _Unsupported("")
        values[name] = raw
    if values["fill"] == "none" and values["stroke"] == "none":
        raise _Unsupported("")
    css = []
    if values["fill"] != "none":
        css.append(f"background:{values['fill']}")
    if values["stroke"] != "none":
        width = _number(elem, "stroke-width", 1.0) * scale
        if width <= 0:
            raise _Unsupported("")
        css.append(f"border:{width:g}px solid {values['stroke']}")
    if elem.get("opacity") is not None:
        css.append(f"opacity:{_number(elem, 'opacity'):g}")
    return ";".join(css)


def _shape(elem: ET.Element, scale: float, dx: float = 0.0, dy: float = 0.0) -> str:
    """A plain rectangle, ellipse or line as the section's own shape, in the same place with the
    same paint; `dx`, `dy` are the translate of the group it sits in."""
    tag = _local(elem)
    if set(elem.attrib) - _SHAPE_ATTRS[tag]:
        raise _Unsupported("")
    kind, extra = "rect", ""
    if tag == "rect":
        x, y = _number(elem, "x", 0.0) + dx, _number(elem, "y", 0.0) + dy
        w, h = _number(elem, "width"), _number(elem, "height")
        rx = _number(elem, "rx", _number(elem, "ry", 0.0))
        if rx != _number(elem, "ry", rx) or rx < 0 or rx > min(w, h) / 2:
            raise _Unsupported("")
        if rx:
            kind, extra = "round-rect", f";border-radius:{rx * scale:g}px"
    elif tag == "line":
        ends = [
            (_number(elem, "x1") + dx, _number(elem, "y1") + dy),
            (_number(elem, "x2") + dx, _number(elem, "y2") + dy),
        ]
        (x, y), (x2, y2) = sorted(ends)
        if y2 < y:
            raise _Unsupported("")
        w, h, kind = x2 - x, y2 - y, "line"
    else:
        cx, cy = _number(elem, "cx") + dx, _number(elem, "cy") + dy
        rx = _number(elem, "r") if tag == "circle" else _number(elem, "rx")
        ry = rx if tag == "circle" else _number(elem, "ry")
        x, y, w, h, kind = cx - rx, cy - ry, 2 * rx, 2 * ry, "ellipse"
    if (w < 0 or h < 0) or (kind != "line" and (w == 0 or h == 0)):
        raise _Unsupported("")
    css = _paint(elem, scale, fill=kind != "line")
    box = f"left:{x * scale:g}px;top:{y * scale:g}px;width:{w * scale:g}px;height:{h * scale:g}px"
    ident = f' id="{_attr(elem.get("id", ""))}"' if elem.get("id") else ""
    return f'<x-shape{ident} data-shape="{kind}" style="{box};{css}{extra}"/>'


def _group_shapes(group: ET.Element, scale: float) -> list[str] | None:
    """A group that only moves (a translate) and holds nothing but plain shapes and texts, as
    its shapes one by one; None when anything in it needs the drawing."""
    if set(group.attrib) - {"id", "transform"}:
        return None
    dx = dy = 0.0
    if group.get("transform"):
        moved = _TRANSLATE.fullmatch(group.get("transform", ""))
        if moved is None:
            return None
        dx, dy = float(moved.group(1)), float(moved.group(2) or 0)
    shapes = []
    for child in group:
        tag = _local(child)
        if tag in _NON_VISUAL or tag == "text":
            continue
        if tag not in _SHAPE_ATTRS:
            return None
        try:
            shapes.append(_shape(child, scale, dx, dy))
        except _Unsupported:
            return None
    return shapes or None


def _icon(elem: ET.Element, scale: float) -> str:
    size = float(elem.get("width", elem.get("height", "24")))
    x, y = float(elem.get("x", "0")), float(elem.get("y", "0"))
    colour = elem.get("stroke") or elem.get("fill") or elem.get("color") or "#1F2937"
    if elem.get("transform") or elem.get("stroke-width"):
        raise _Unsupported("an icon with a transform or its own line weight")
    ident = f' id="{_attr(elem.get("id", ""))}"' if elem.get("id") else ""
    s = scale
    return (
        f'<x-icon{ident} data-icon="{_attr(elem.get("data-icon", ""))}" style="left:{x * s:g}px;'
        f'top:{y * s:g}px;width:{size * s:g}px;height:{size * s:g}px;color:{colour}"/>'
    )


def _chart(elem: ET.Element, scale: float) -> str:
    spec = _native_spec(elem)
    box = _spec_box(spec, scale)
    if "font_size" in spec:
        spec["font_size"] = spec["font_size"] * scale
    ident = f' id="{_attr(elem.get("id", ""))}"' if elem.get("id") else ""
    data = escape(json.dumps(spec, ensure_ascii=False))
    return f'<x-chart{ident} style="{box}">{data}</x-chart>'


def _table(elem: ET.Element, scale: float) -> str:
    spec = _native_spec(elem)
    style = spec.get("style") or {}
    if set(spec) - _TABLE_KEYS or set(style) - _TABLE_STYLE_KEYS:
        raise _Unsupported("table fields the section table has no place for")
    heights = spec.get("row_heights")
    if heights and len(set(heights)) > 1:
        raise _Unsupported("a table with uneven rows")
    rows = ([spec["columns"]] if spec.get("columns") else []) + list(spec.get("rows", []))
    header_rows = int(spec.get("header_rows", 1 if spec.get("columns") else 0))
    width = float(spec.get("width", 0)) * scale
    box = _spec_box(spec, scale)
    css = [box, f"font-size:{float(style.get('font_size', 18)) * scale:g}px"]
    for key, prop in (
        ("font_family", "font-family"),
        ("body_text", "color"),
        ("body_fill", "background"),
        ("border_color", "border-color"),
    ):
        if style.get(key):
            css.append(f"{prop}:{style[key]}")
    ident = f' id="{_attr(elem.get("id", ""))}"' if elem.get("id") else ""
    body = _table_rows(rows, header_rows, style, spec.get("column_widths"), width)
    return f'<table{ident} style="{";".join(css)}">{body}</table>'


def _table_rows(
    rows: list[list[Any]],
    header_rows: int,
    style: dict[str, Any],
    widths: list[float] | None,
    width: float,
) -> str:
    out = []
    if widths:
        total = sum(widths)
        cols = "".join(f'<col style="width:{width * w / total:g}px"/>' for w in widths)
        out.append(f"<colgroup>{cols}</colgroup>")
    covered: set[tuple[int, int]] = set()
    band = style.get("band_fill") if style.get("band_row", True) else None
    for r, row in enumerate(rows):
        cells = []
        for c, cell in enumerate(row):
            if (r, c) in covered:
                continue
            data = cell if isinstance(cell, dict) else {"text": "" if cell is None else str(cell)}
            if set(data) - _CELL_KEYS:
                raise _Unsupported("table cells with runs or their own spacing")
            for dr in range(int(data.get("row_span", 1))):
                for dc in range(int(data.get("col_span", 1))):
                    if dr or dc:
                        covered.add((r + dr, c + dc))
            header = r < header_rows
            fill = data.get("fill") or (style.get("header_fill") if header else None)
            if not fill and not header and band and r % 2 == 0 and r:
                fill = band
            colour = data.get("color") or (style.get("header_text") if header else None)
            cells.append(_cell(data, "th" if header else "td", fill, colour))
        out.append(f"<tr>{''.join(cells)}</tr>")
    return "".join(out)


def _cell(data: dict[str, Any], tag: str, fill: str | None, colour: str | None) -> str:
    css = []
    if data.get("align"):
        css.append(f"text-align:{_ALIGN.get(str(data['align']), 'left')}")
    if colour:
        css.append(f"color:{colour}")
    if fill:
        css.append(f"background:{fill}")
    if "bold" in data:
        css.append(f"font-weight:{'bold' if data['bold'] else 'normal'}")
    attrs = f' style="{";".join(css)}"' if css else ""
    for key, name in (("col_span", "colspan"), ("row_span", "rowspan")):
        if int(data.get(key, 1)) > 1:
            attrs += f' {name}="{int(data[key])}"'
    text = "<br/>".join(escape(line) for line in str(data.get("text", "")).split("\n"))
    return f"<{tag}{attrs}>{text}</{tag}>"


def _native_spec(elem: ET.Element) -> dict[str, Any]:
    metadata = next((c for c in elem if _local(c) == "metadata"), None)
    try:
        spec = json.loads(metadata.text or "") if metadata is not None else None
    except ValueError:
        spec = None
    if not isinstance(spec, dict) or elem.get("transform"):
        raise _Unsupported("a chart or table without plain JSON data")
    return spec


def _spec_box(spec: dict[str, Any], scale: float) -> str:
    try:
        x, y, w, h = (float(spec.pop(k)) * scale for k in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError):
        raise _Unsupported("a chart or table without its box") from None
    return f"left:{x:g}px;top:{y:g}px;width:{w:g}px;height:{h:g}px"


def _box(elem: ET.Element, scale: float) -> str:
    values = [float(elem.get(k, "0")) * scale for k in ("x", "y", "width", "height")]
    return "left:{:g}px;top:{:g}px;width:{:g}px;height:{:g}px".format(*values)


def _bounds(elem: ET.Element, ctx: ConvertContext) -> tuple[float, float, float, float] | None:
    """The element's box on the page, from what the compiler draws for it."""
    probe = copy.deepcopy(ctx)
    result = convert_element(copy.deepcopy(elem), probe, PageReport("bounds"))
    if result is None:
        return None
    if result.bounds_emu is not None:
        x0, y0, x1, y1 = result.bounds_emu
    else:
        shapes = etree.fromstring(f"<w {NSDECL}>{result.xml}</w>")
        boxes = []
        for xfrm in shapes.iter(f"{_A}xfrm"):
            off, ext = xfrm.find(f"{_A}off"), xfrm.find(f"{_A}ext")
            if off is not None and ext is not None:
                x, y = int(off.get("x")), int(off.get("y"))
                boxes.append((x, y, x + int(ext.get("cx")), y + int(ext.get("cy"))))
        if not boxes:
            return None
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    return (
        x0 / PAGE_EMU_PER_PX,
        y0 / PAGE_EMU_PER_PX,
        (x1 - x0) / PAGE_EMU_PER_PX,
        (y1 - y0) / PAGE_EMU_PER_PX,
    )


def _group_context(group: ET.Element, ctx: ConvertContext) -> ConvertContext:
    """The context the compiler gives a group's children: its translate and scale."""
    from .compiler import _TRANSLATE_SCALE

    match = _TRANSLATE_SCALE.fullmatch(group.get("transform", ""))
    if match is None:
        raise SectionError(f"{_label(group)}: a group takes translate() and scale() only")
    tx, ty = float(match["tx"] or 0), float(match["ty"] or 0)
    sx = float(match["sx"] or 1)
    sy = float(match["sy"] or match["sx"] or 1)
    child = ctx.child(
        dx=tx * ctx.scale_x,
        dy=ty * ctx.scale_y,
        sx=sx,
        sy=sy,
        style_overrides=utils._extract_inheritable_styles(group),
    )
    child.depth = ctx.depth + 1
    return child


def _texts_in(group: ET.Element, ctx: ConvertContext) -> list[tuple[ET.Element, ConvertContext]]:
    """Every text under `group`, with the context the compiler converts it in."""
    inner = _group_context(group, ctx)
    found: list[tuple[ET.Element, ConvertContext]] = []
    for child in group:
        if _local(child) == "text":
            found.append((child, inner))
        elif _local(child) == "g" and any(_local(d) == "text" for d in child.iter()):
            if native.native_kind(child):
                raise _Unsupported("a chart or table inside a group with text")
            found.extend(_texts_in(child, inner))
    return found


def _remove_texts(group: ET.Element) -> None:
    for parent in list(group.iter()):
        for child in list(parent):
            if _local(child) == "text":
                parent.remove(child)


def _background(page: ET.Element) -> str | None:
    """A full-page solid rectangle drawn first is the slide's background, as the compiler has it."""
    first = next((c for c in page if _local(c) not in _NON_VISUAL), None)
    if first is None or _local(first) != "rect" or first.get("transform"):
        return None
    view = page.get("viewBox", "").replace(",", " ").split()
    full = (first.get("x", "0"), first.get("y", "0"), first.get("width"), first.get("height"))
    if len(view) != 4 or tuple(float(v or "nan") for v in full) != tuple(float(v) for v in view):
        return None
    fill = first.get("fill", "")
    if len(fill) != 7 or not fill.startswith("#") or first.get("rx") or first.get("stroke"):
        return None
    page.remove(first)
    return fill[1:].upper()


def _notes(page: ET.Element) -> list[str]:
    desc = next((c for c in page if _local(c) == "desc" and c.get("id") == "notes"), None)
    text = "".join(desc.itertext()) if desc is not None else ""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _defs_holder(defs: list[ET.Element]) -> str:
    body = "".join(_svg_markup(d) for d in defs)
    return (
        f'<svg xmlns="{SVG_NS}" viewBox="0 0 1 1" style="left:0px;top:0px;width:1px;height:1px">'
        f"{body}</svg>"
    )


def _svg_markup(elem: ET.Element) -> str:
    ET.register_namespace("", SVG_NS)
    text = ET.tostring(elem, encoding="unicode")
    return text.replace(f' xmlns="{SVG_NS}"', "", 1)


def _local(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1] if isinstance(elem.tag, str) else ""


def _label(elem: ET.Element) -> str:
    return f'<{_local(elem)} id="{elem.get("id")}">' if elem.get("id") else f"<{_local(elem)}>"


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})
