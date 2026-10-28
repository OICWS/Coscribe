"""How a Word paragraph, run and table cell look once its styles and direct formatting are resolved,
so the Docs editor can draw a document the way Word does. Display only: the editor never sends a
paragraph's look back, and a save leaves the paragraph properties in the file as they are."""

from __future__ import annotations

import re
from typing import Any

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_CJK = re.compile(r"[⺀-鿿豈-﫿＀-￯]")
_THEME_NAMES = {
    "text1": "dk1",
    "background1": "lt1",
    "text2": "dk2",
    "background2": "lt2",
    "hyperlink": "hlink",
    "followedHyperlink": "folHlink",
}
_ALIGN = {
    "left": "left",
    "start": "left",
    "center": "center",
    "right": "right",
    "end": "right",
    "both": "justify",
}
_SIDES = ("top", "left", "bottom", "right")


def _q(name: str) -> str:
    return f"{{{_W}}}{name}"


def _attr(element: Any, name: str) -> str | None:
    value = element.get(_q(name)) if element is not None else None
    return value if isinstance(value, str) else None


def _val(element: Any, name: str) -> str | None:
    child = element.find(_q(name)) if element is not None else None
    return _attr(child, "val")


def _twips(value: str | None) -> float | None:
    try:
        return round(int(value) / 20, 2) if value is not None else None
    except ValueError:
        return None


def _shade(channel: int, factor: float) -> int:
    return max(0, min(255, round(channel * factor)))


def _tinted(hex6: str, shade: str | None, tint: str | None) -> str:
    red, green, blue = (int(hex6[i : i + 2], 16) for i in (0, 2, 4))
    if shade:
        factor = int(shade, 16) / 255
        red, green, blue = (_shade(c, factor) for c in (red, green, blue))
    if tint:
        factor = int(tint, 16) / 255
        red, green, blue = (round(c + (255 - c) * (1 - factor)) for c in (red, green, blue))
    return f"{red:02X}{green:02X}{blue:02X}"


class Looks:
    def __init__(self, document: Any) -> None:
        styles = document.styles.element
        self._styles = {s.get(_q("styleId")): s for s in styles.findall(_q("style"))}
        self._defaults = styles.find(_q("docDefaults"))
        self._theme_colours: dict[str, str] = {}
        self._theme_fonts: dict[str, str] = {}
        self._read_theme(document)

    def _read_theme(self, document: Any) -> None:
        from lxml import etree

        for part in document.part.package.iter_parts():
            if str(part.partname).endswith("/theme/theme1.xml"):
                try:
                    root = etree.fromstring(part.blob)
                except etree.XMLSyntaxError:
                    return
                scheme = root.find(f".//{{{_A}}}clrScheme")
                for colour in scheme if scheme is not None else []:
                    inner = colour[0] if len(colour) else None
                    value = inner.get("val") or inner.get("lastClr") if inner is not None else None
                    if value and re.fullmatch(r"[0-9A-Fa-f]{6}", value):
                        self._theme_colours[etree.QName(colour).localname] = value.upper()
                for kind in ("major", "minor"):
                    latin = root.find(f".//{{{_A}}}{kind}Font/{{{_A}}}latin")
                    if latin is not None and latin.get("typeface"):
                        self._theme_fonts[kind] = latin.get("typeface", "")
                return

    # -- Styles ----------------------------------------------------------------------------------

    def _chain(self, style_id: str | None) -> list[Any]:
        """The style and what it is based on, the base first."""
        found: list[Any] = []
        seen: set[str] = set()
        while style_id and style_id in self._styles and style_id not in seen:
            seen.add(style_id)
            found.append(self._styles[style_id])
            style_id = _val(self._styles[style_id], "basedOn")
        return found[::-1]

    def _default_style(self, kind: str) -> str | None:
        for style in self._styles.values():
            if style.get(_q("type")) == kind and style.get(_q("default")) in ("1", "true"):
                return _attr(style, "styleId")
        return None

    # -- Run properties --------------------------------------------------------------------------

    def _colour(self, element: Any) -> str | None:
        if element is None:
            return None
        theme = element.get(_q("themeColor"))
        value = element.get(_q("val"))
        if theme:
            base = self._theme_colours.get(_THEME_NAMES.get(theme, theme))
            if base:
                return _tinted(base, element.get(_q("themeShade")), element.get(_q("themeTint")))
        if value and re.fullmatch(r"[0-9A-Fa-f]{6}", value):
            return str(value).upper()
        return None

    def _font(self, element: Any) -> str | None:
        if element is None:
            return None
        for theme_key, key in (("eastAsiaTheme", "eastAsia"), ("asciiTheme", "ascii")):
            theme = element.get(_q(theme_key))
            if theme and not theme.endswith("Bidi"):
                font = self._theme_fonts.get("major" if theme.startswith("major") else "minor")
                if font:
                    return font
            if element.get(_q(key)):
                return _attr(element, key)
        return _attr(element, "hAnsi")

    def _run_props(self, sources: list[Any]) -> dict[str, Any]:
        """The run properties of `w:rPr` elements, the last one winning."""
        look: dict[str, Any] = {}
        for props in sources:
            if props is None:
                continue
            if (font := self._font(props.find(_q("rFonts")))) is not None:
                look["font"] = font
            if (size := _val(props, "sz")) and size.isdigit():
                look["size"] = int(size) / 2
            if (colour := self._colour(props.find(_q("color")))) is not None:
                look["color"] = colour
            for tag, key in (("b", "b"), ("i", "i")):
                node = props.find(_q(tag))
                if node is not None:
                    look[key] = node.get(_q("val"), "true") not in ("0", "false", "off")
        return look

    # -- Paragraphs ------------------------------------------------------------------------------

    def paragraph(self, paragraph: Any | None) -> dict[str, Any]:
        """Alignment, spacing, borders, fill and the default look of a paragraph's text (None: the
        document's own)."""
        properties = paragraph.find(_q("pPr")) if paragraph is not None else None
        style_id = _val(properties, "pStyle") or self._default_style("paragraph")
        chain = self._chain(style_id)
        defaults = self._defaults
        runs = [
            defaults.find(f"{_q('rPrDefault')}/{_q('rPr')}") if defaults is not None else None,
            *(s.find(_q("rPr")) for s in chain),
        ]
        looks = [
            defaults.find(f"{_q('pPrDefault')}/{_q('pPr')}") if defaults is not None else None,
            *(s.find(_q("pPr")) for s in chain),
            properties,
        ]
        look = self._run_props(runs)
        for node in looks:
            if node is not None:
                self._paragraph_props(node, look)
        return look

    def _paragraph_props(self, node: Any, look: dict[str, Any]) -> None:
        if (align := _val(node, "jc")) in _ALIGN:
            look["align"] = _ALIGN[align or ""]
        spacing = node.find(_q("spacing"))
        if spacing is not None:
            for name, key in (("before", "before"), ("after", "after")):
                if (points := _twips(spacing.get(_q(name)))) is not None:
                    look[key] = points
            line = spacing.get(_q("line"))
            if line and line.isdigit():
                exact = spacing.get(_q("lineRule"), "auto") != "auto"
                look["line"] = {"pt": int(line) / 20} if exact else {"m": round(int(line) / 240, 3)}
        indent = node.find(_q("ind"))
        if indent is not None:
            for name, key in (
                ("left", "left"),
                ("start", "left"),
                ("right", "right"),
                ("end", "right"),
            ):
                if (points := _twips(indent.get(_q(name)))) is not None:
                    look[key] = points
            if (points := _twips(indent.get(_q("firstLine")))) is not None:
                look["first"] = points
            if (points := _twips(indent.get(_q("hanging")))) is not None:
                look["first"] = -points
        borders = node.find(_q("pBdr"))
        if borders is not None:
            drawn = {
                side: edge
                for side in _SIDES
                if (edge := self._edge(borders.find(_q(side)))) is not None
            }
            if drawn:
                look["border"] = drawn
        shading = node.find(_q("shd"))
        if (
            shading is not None
            and (fill := shading.get(_q("fill")))
            and re.fullmatch(r"[0-9A-Fa-f]{6}", fill)
        ):
            look["fill"] = fill.upper()

    def _edge(self, element: Any) -> dict[str, Any] | None:
        if element is None or element.get(_q("val")) in (None, "nil", "none"):
            return None
        size = element.get(_q("sz"), "4")
        raw = element.get(_q("color"))
        colour = raw.upper() if raw and re.fullmatch(r"[0-9A-Fa-f]{6}", raw) else "000000"
        return {"c": colour, "w": round(int(size) / 8, 2) if size.isdigit() else 0.5}

    def run(self, run: Any, base: dict[str, Any], text: str) -> dict[str, Any]:
        """What a run's own formatting adds to its paragraph's look: colour, size and font."""
        style_id = _val(run.find(_q("rPr")), "rStyle")
        own = self._run_props(
            [*(s.find(_q("rPr")) for s in self._chain(style_id)), run.find(_q("rPr"))]
        )
        marks: dict[str, Any] = {}
        if own.get("color") and own["color"] != base.get("color"):
            marks["c"] = own["color"]
        if own.get("size") and own["size"] != base.get("size"):
            marks["sz"] = own["size"]
        if own.get("font") and own["font"] != base.get("font"):
            marks["f"] = own["font"]
        return marks if text or marks else {}

    # -- Tables ----------------------------------------------------------------------------------

    def cell(self, cell: Any) -> dict[str, Any]:
        """Fill, borders, padding and alignment of a table cell."""
        look: dict[str, Any] = {}
        props = cell.find(_q("tcPr"))
        if props is None:
            return look
        shading = props.find(_q("shd"))
        if (
            shading is not None
            and (fill := shading.get(_q("fill")))
            and re.fullmatch(r"[0-9A-Fa-f]{6}", fill)
        ):
            look["fill"] = fill.upper()
        borders = props.find(_q("tcBorders"))
        if borders is not None:
            look["border"] = {
                side: edge
                for side in _SIDES
                if (edge := self._edge(borders.find(_q(side)))) is not None
            }
        margins = props.find(_q("tcMar"))
        if margins is not None:
            look["pad"] = {
                side: points
                for side in _SIDES
                if (points := _twips(_margin(margins, side))) is not None
            }
        if (align := _val(props, "vAlign")) in ("center", "bottom"):
            look["valign"] = "middle" if align == "center" else "bottom"
        return look

    def table_widths(self, table: Any) -> list[float]:
        grid = table.find(_q("tblGrid"))
        widths = [
            _twips(c.get(_q("w")))
            for c in (grid.findall(_q("gridCol")) if grid is not None else [])
        ]
        return [w for w in widths if w is not None]

    def table_edges(self, table: Any) -> dict[str, Any]:
        """Borders a table draws around and between its cells: its style's, then its own."""
        names = (*_SIDES, "insideH", "insideV")
        edges: dict[str, Any] = {}
        for source in (*self._table_styles(table), table):
            borders = source.find(f"{_q('tblPr')}/{_q('tblBorders')}")
            if borders is None:
                continue
            for name in names:
                if (edge := self._edge(borders.find(_q(name)))) is not None:
                    edges[name] = edge
        return edges

    def _table_styles(self, table: Any) -> list[Any]:
        return self._chain(_val(table.find(_q("tblPr")), "tblStyle"))

    def table_row_look(self, table: Any, row: int, rows: int) -> dict[str, Any]:
        """What the table's style gives a whole row: the first and the last row, when the table's
        look turns them on. `fill` and `border` are the cell's, `color` and `b` its text's."""
        flags = table.find(f"{_q('tblPr')}/{_q('tblLook')}")
        kinds = []
        if row == 0 and _table_flag(flags, "firstRow", 0x0020):
            kinds.append("firstRow")
        if row == rows - 1 and rows > 1 and _table_flag(flags, "lastRow", 0x0040):
            kinds.append("lastRow")
        look: dict[str, Any] = {}
        for style in self._table_styles(table):
            for part in style.findall(_q("tblStylePr")):
                if part.get(_q("type")) not in kinds:
                    continue
                shading = part.find(f"{_q('tcPr')}/{_q('shd')}")
                fill = shading.get(_q("fill")) if shading is not None else None
                if fill and re.fullmatch(r"[0-9A-Fa-f]{6}", fill):
                    look["fill"] = fill.upper()
                borders = part.find(f"{_q('tcPr')}/{_q('tcBorders')}")
                if borders is not None:
                    look["border"] = {
                        **look.get("border", {}),
                        **{
                            side: edge
                            for side in _SIDES
                            if (edge := self._edge(borders.find(_q(side)))) is not None
                        },
                    }
                text = part.find(_q("rPr"))
                if (colour := self._colour(text.find(_q("color"))) if text is not None else None):
                    look["color"] = colour
                if text is not None and text.find(_q("b")) is not None:
                    look["b"] = True
        return look


def _table_flag(look: Any, name: str, bit: int) -> bool:
    """Whether a table's `tblLook` turns a conditional part on: as an attribute, else in the
    hexadecimal `val` of older files."""
    if look is None:
        return False
    if (flag := look.get(_q(name))) is not None:
        return flag in ("1", "true", "on")
    value = look.get(_q("val"))
    return bool(value and re.fullmatch(r"[0-9A-Fa-f]{1,4}", value) and int(value, 16) & bit)


def _margin(margins: Any, side: str) -> str | None:
    for name in (side, {"left": "start", "right": "end"}.get(side, side)):
        element = margins.find(_q(name))
        if element is not None:
            return _attr(element, "w")
    return None


def page_of(document: Any, looks: Looks) -> dict[str, Any]:
    """The page the document is laid out on and the look of its ordinary text, in points."""
    section = document.sections[0]
    sizes = {
        "w": section.page_width,
        "h": section.page_height,
        "l": section.left_margin,
        "r": section.right_margin,
        "t": section.top_margin,
        "b": section.bottom_margin,
    }
    return {
        **{k: round(v / 12700, 1) for k, v in sizes.items() if v is not None},
        "base": looks.paragraph(None),
    }
