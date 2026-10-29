"""What a slide shows beneath the page that drew it (decision 0016): its background, the master's
and the layout's own shapes, and the shapes the page took over from a template slide
(`data-template-slide`). A deck built on the user's template carries its look there, not in the
pages, so without this the panel and the cards show a bare page.

A subset of DrawingML, drawn as SVG in page px: a few preset shapes, custom paths, pictures,
groups, solid and linear gradient fills, outlines and plain text. A shape it cannot draw is left
out rather than drawn wrong.
"""

from __future__ import annotations

import base64
import colorsys
import math
from collections.abc import Callable
from html import escape
from typing import Any

from lxml import etree
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_SHAPES = {"sp", "pic", "grpSp", "cxnSp", "graphicFrame"}
# The master's colour map names these slots by the role a shape asks for.
_ROLES = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
_PRESET = {"black": "000000", "white": "FFFFFF", "red": "FF0000", "gray": "808080"}
_IMAGE_TYPES = {"png": "image/png", "jpeg": "image/jpeg", "jpg": "image/jpeg", "gif": "image/gif"}
# A paragraph without its own size: PowerPoint's default body size, in points.
_DEFAULT_PT = 18
_EMU_PER_PT = 12700
# A text box's default insets, in EMU, when its bodyPr names none.
_INSETS = {"lIns": 91440, "tIns": 45720, "rIns": 91440, "bIns": 45720}


def template_shapes(slide: Any, count: int) -> list[Any]:
    """The first `count` shapes of the slide's tree: the build puts a template slide's shapes
    there, before the page's own."""
    return [el for el in slide.shapes._spTree if _tag(el) in _SHAPES][:count]


def underlay(slide: Any, copied: list[Any], emu_per_px: float) -> str:
    """The SVG markup of everything the slide shows under its page's own shapes, in page px."""
    layout = slide.slide_layout
    master = layout.slide_master
    painter = _Painter(master, emu_per_px)
    out = [_background(painter, slide, layout, master)]
    if slide.element.get("showMasterSp", "1") != "0":
        if layout.element.get("showMasterSp", "1") != "0":
            out += painter.tree(master.shapes._spTree, master.part)
        out += painter.tree(layout.shapes._spTree, layout.part)
    out += [painter.shape(el, slide.part) for el in copied]
    defs = f"<defs>{''.join(painter.defs)}</defs>" if painter.defs else ""
    return defs + "".join(out)


def _slide_size(slide: Any) -> tuple[int, int]:
    prs = slide.part.package.presentation_part.presentation
    return int(prs.slide_width or 0), int(prs.slide_height or 0)


def _background(painter: _Painter, slide: Any, layout: Any, master: Any) -> str:
    """The first of the slide's, the layout's and the master's backgrounds, as a full rect."""
    width, height = (v / painter.scale for v in _slide_size(slide))
    for owner in (slide, layout, master):
        bg = owner.element.find(f"{_P}cSld/{_P}bg")
        if bg is None:
            continue
        props = bg.find(f"{_P}bgPr")
        if props is not None:
            fill = painter.fill(props, owner.part)
        else:
            ref = bg.find(f"{_P}bgRef")
            fill = painter.colour(ref) if ref is not None else None
        if fill is None:
            return ""
        return f'<rect x="0" y="0" width="{width:.2f}" height="{height:.2f}" fill="{fill}"/>'
    return ""


def _tag(el: Any) -> str:
    return el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""


class _Painter:
    def __init__(self, master: Any, emu_per_px: float) -> None:
        self.scale = emu_per_px
        self.defs: list[str] = []
        theme = etree.fromstring(master.part.part_related_by(RT.THEME).blob)
        self.scheme: dict[str, str] = {}
        scheme = theme.find(f".//{_A}clrScheme")
        for slot in scheme if scheme is not None else []:
            value = _plain_colour(slot)
            if value:
                self.scheme[_tag(slot)] = value
        mapping = master.element.find(f"{_P}clrMap")
        self.roles = dict(_ROLES)
        if mapping is not None:
            self.roles.update({role: mapping.get(role, slot) for role, slot in _ROLES.items()})
        self._gradients = 0

    def tree(self, tree: Any, part: Any) -> list[str]:
        return [self.shape(el, part) for el in tree if _tag(el) in _SHAPES]

    def shape(self, el: Any, part: Any) -> str:
        """One shape, or "" for a placeholder (only its prompt shows, in editing) and for what
        this subset does not draw."""
        if el.find(f"./*/{_P}nvPr/{_P}ph") is not None:
            return ""
        tag = _tag(el)
        try:
            if tag == "grpSp":
                return self._group(el, part)
            if tag == "pic":
                return self._picture(el, part)
            if tag in ("sp", "cxnSp"):
                return self._sp(el, part)
        except (KeyError, ValueError, ZeroDivisionError, AttributeError):
            return ""
        return ""

    # Geometry

    def _xfrm(self, el: Any) -> Any:
        return (
            el.find(f"{_P}spPr/{_A}xfrm")
            if _tag(el) != "grpSp"
            else el.find(f"{_P}grpSpPr/{_A}xfrm")
        )

    def _box(self, xfrm: Any) -> tuple[float, float, float, float]:
        off, ext = xfrm.find(f"{_A}off"), xfrm.find(f"{_A}ext")
        return (
            int(off.get("x", 0)) / self.scale,
            int(off.get("y", 0)) / self.scale,
            int(ext.get("cx", 0)) / self.scale,
            int(ext.get("cy", 0)) / self.scale,
        )

    def _transform(self, xfrm: Any, box: tuple[float, float, float, float]) -> str:
        """Rotation and flips about the box's centre, as an SVG transform attribute."""
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        steps = []
        rotation = int(xfrm.get("rot", 0)) / 60000
        if rotation:
            steps.append(f"rotate({rotation:.2f} {cx:.2f} {cy:.2f})")
        flip_x = -1 if xfrm.get("flipH") == "1" else 1
        flip_y = -1 if xfrm.get("flipV") == "1" else 1
        if flip_x < 0 or flip_y < 0:
            steps.append(
                f"translate({cx:.2f} {cy:.2f}) scale({flip_x} {flip_y}) "
                f"translate({-cx:.2f} {-cy:.2f})"
            )
        return f' transform="{" ".join(steps)}"' if steps else ""

    def _group(self, el: Any, part: Any) -> str:
        xfrm = self._xfrm(el)
        if xfrm is None:
            return "".join(self.tree(el, part))
        x, y, w, h = self._box(xfrm)
        child_off, child_ext = xfrm.find(f"{_A}chOff"), xfrm.find(f"{_A}chExt")
        cx = int(child_off.get("x", 0)) / self.scale if child_off is not None else x
        cy = int(child_off.get("y", 0)) / self.scale if child_off is not None else y
        cw = int(child_ext.get("cx", 0)) / self.scale if child_ext is not None else w
        ch = int(child_ext.get("cy", 0)) / self.scale if child_ext is not None else h
        sx, sy = (w / cw if cw else 1), (h / ch if ch else 1)
        inner = "".join(self.tree(el, part))
        mapping = (
            f"translate({x:.2f} {y:.2f}) scale({sx:.5f} {sy:.5f}) translate({-cx:.2f} {-cy:.2f})"
        )
        return f'<g{self._transform(xfrm, (x, y, w, h))}><g transform="{mapping}">{inner}</g></g>'

    def _sp(self, el: Any, part: Any) -> str:
        xfrm = self._xfrm(el)
        if xfrm is None:
            return ""
        box = self._box(xfrm)
        props = el.find(f"{_P}spPr")
        outline = self._outline(props.find(f"{_A}ln"), el.find(f"{_P}style"), part)
        if _tag(el) == "cxnSp":
            fill = "none"
        else:
            fill = self.fill(props, part) or self._style_fill(el.find(f"{_P}style")) or "none"
        drawn = _geometry(props, box)
        if drawn is None:
            return ""
        text = self._text(el.find(f"{_P}txBody"), box)
        shape = drawn.format(paint=f'fill="{fill}"{outline}')
        return f"<g{self._transform(xfrm, box)}>{shape}{text}</g>"

    def _picture(self, el: Any, part: Any) -> str:
        xfrm = self._xfrm(el)
        blip = el.find(f"{_P}blipFill/{_A}blip")
        if xfrm is None or blip is None:
            return ""
        x, y, w, h = self._box(xfrm)
        uri = _image_uri(part, blip.get(f"{_R}embed", ""))
        if uri is None:
            return ""
        crop = el.find(f"{_P}blipFill/{_A}srcRect")
        image = f'<image x="0" y="0" width="1" height="1" preserveAspectRatio="none" href="{uri}"/>'
        if crop is not None:
            left, top, right, bottom = (
                int(crop.get(side, 0)) / 100000 for side in ("l", "t", "r", "b")
            )
            shown_w, shown_h = 1 - left - right, 1 - top - bottom
            if shown_w > 0 and shown_h > 0:
                image = (
                    f'<svg x="0" y="0" width="1" height="1" preserveAspectRatio="none" '
                    f'viewBox="{left:.5f} {top:.5f} {shown_w:.5f} {shown_h:.5f}">{image}</svg>'
                )
        placed = f'<g transform="translate({x:.2f} {y:.2f}) scale({w:.4f} {h:.4f})">{image}</g>'
        return f"<g{self._transform(xfrm, (x, y, w, h))}>{placed}</g>"

    # Paint

    def fill(self, props: Any, part: Any) -> str | None:
        """The SVG paint for a shape's or background's fill: a colour, a gradient's url(), or
        "none"; None when the properties name no fill (the style's then applies)."""
        for child in props:
            kind = _tag(child)
            if kind == "noFill":
                return "none"
            if kind == "solidFill":
                return self.colour(child)
            if kind == "gradFill":
                return self._gradient(child)
            if kind == "blipFill":
                return self._picture_fill(child, part)
        return None

    def _style_fill(self, style: Any) -> str | None:
        ref = style.find(f"{_A}fillRef") if style is not None else None
        if ref is None or ref.get("idx", "0") == "0":
            return None
        return self.colour(ref)

    def _outline(self, line: Any, style: Any, part: Any) -> str:
        colour = None
        if line is not None:
            colour = self.fill(line, part)
        if colour is None and style is not None:
            ref = style.find(f"{_A}lnRef")
            if ref is not None and ref.get("idx", "0") != "0":
                colour = self.colour(ref)
        if not colour or colour == "none" or colour.startswith("url("):
            return ""
        width = int(line.get("w", 9525)) / self.scale if line is not None else 1.0
        return f' stroke="{colour}" stroke-width="{max(width, 0.5):.2f}"'

    def colour(self, holder: Any) -> str | None:
        """The colour of the first colour element under `holder`, its modifiers applied, as
        #RRGGBB or rgba()."""
        for node in holder:
            kind = _tag(node)
            base = None
            if kind == "srgbClr":
                base = node.get("val")
            elif kind == "schemeClr":
                slot = node.get("val", "")
                base = self.scheme.get(self.roles.get(slot, slot))
            elif kind == "sysClr":
                base = node.get("lastClr")
            elif kind == "prstClr":
                base = _PRESET.get(node.get("val", ""))
            if base:
                return _modified(base, node)
        return None

    def _gradient(self, grad: Any) -> str | None:
        stops = []
        for stop in grad.iter(f"{_A}gs"):
            colour = self.colour(stop)
            if colour:
                stops.append((int(stop.get("pos", 0)) / 1000, colour))
        if not stops:
            return None
        if len(stops) == 1:
            return stops[0][1]
        self._gradients += 1
        name = f"tl-grad-{self._gradients}"
        lin = grad.find(f"{_A}lin")
        angle = math.radians(int(lin.get("ang", 0)) / 60000) if lin is not None else 0.0
        dx, dy = math.cos(angle) / 2, math.sin(angle) / 2
        coords = f'x1="{0.5 - dx:.3f}" y1="{0.5 - dy:.3f}" x2="{0.5 + dx:.3f}" y2="{0.5 + dy:.3f}"'
        body = "".join(f'<stop offset="{pos:.1f}%" stop-color="{c}"/>' for pos, c in stops)
        self.defs.append(f'<linearGradient id="{name}" {coords}>{body}</linearGradient>')
        return f"url(#{name})"

    def _picture_fill(self, fill: Any, part: Any) -> str | None:
        blip = fill.find(f"{_A}blip")
        uri = _image_uri(part, blip.get(f"{_R}embed", "")) if blip is not None else None
        if uri is None:
            return None
        self._gradients += 1
        name = f"tl-fill-{self._gradients}"
        self.defs.append(
            f'<pattern id="{name}" patternContentUnits="objectBoundingBox" width="1" height="1">'
            f'<image width="1" height="1" preserveAspectRatio="none" href="{uri}"/></pattern>'
        )
        return f"url(#{name})"

    # Text

    def _text(self, body: Any, box: tuple[float, float, float, float]) -> str:
        """Each paragraph as one line, at its size and colour; enough for a footer or a label a
        template draws, not for wrapped body text."""
        if body is None:
            return ""
        lines = [line for p in body.iter(f"{_A}p") if (line := self._line(p))]
        if not lines:
            return ""
        props = body.find(f"{_A}bodyPr")
        inset = {
            side: int(props.get(side, default) if props is not None else default) / self.scale
            for side, default in _INSETS.items()
        }
        x, y = box[0] + inset["lIns"], box[1] + inset["tIns"]
        w = box[2] - inset["lIns"] - inset["rIns"]
        h = box[3] - inset["tIns"] - inset["bIns"]
        where = props.get("anchor", "t") if props is not None else "t"
        total = sum(line[1] * 1.2 for line in lines)
        top = {"ctr": y + (h - total) / 2, "b": y + h - total}.get(where, y)
        out = []
        for words, size, colour, align, bold in lines:
            top += size * 1.2
            tx, ta = {"ctr": (x + w / 2, "middle"), "r": (x + w, "end")}.get(align, (x, "start"))
            weight = ' font-weight="bold"' if bold else ""
            out.append(
                f'<text x="{tx:.2f}" y="{top - size * 0.25:.2f}" font-size="{size:.2f}" '
                f'fill="{colour}" text-anchor="{ta}"{weight}>{escape(words)}</text>'
            )
        return "".join(out)

    def _line(self, paragraph: Any) -> tuple[str, float, str, str, bool] | None:
        """A paragraph's words, size in px, colour, alignment and weight, from its first run."""
        runs = list(paragraph.iter(f"{_A}r"))
        words = "".join(r.findtext(f"{_A}t") or "" for r in runs)
        if not words.strip():
            return None
        props = runs[0].find(f"{_A}rPr")
        if props is None:
            props = etree.Element(f"{_A}rPr")
        size = int(props.get("sz", _DEFAULT_PT * 100)) / 100 * _EMU_PER_PT / self.scale
        fill = props.find(f"{_A}solidFill")
        colour = (self.colour(fill) if fill is not None else None) or "#000000"
        settings = paragraph.find(f"{_A}pPr")
        align = settings.get("algn", "l") if settings is not None else "l"
        return words, size, colour, align, props.get("b") == "1"


def _geometry(props: Any, box: tuple[float, float, float, float]) -> str | None:
    """The shape's outline as an SVG element with a `{paint}` slot, or None for a preset this
    subset does not know."""
    x, y, w, h = box
    custom = props.find(f"{_A}custGeom")
    if custom is not None:
        return _custom(custom, box)
    preset = props.find(f"{_A}prstGeom")
    name = preset.get("prst", "rect") if preset is not None else "rect"
    drawer = _PRESETS.get(name)
    if drawer is None:
        return None
    adjust = {
        gd.get("name"): int(gd.get("fmla", "val 0").split()[-1])
        for gd in (preset.iter(f"{_A}gd") if preset is not None else [])
        if gd.get("fmla", "").startswith("val ")
    }
    return drawer(x, y, w, h, adjust)


def _poly(*points: tuple[float, float]) -> str:
    return '<polygon points="' + " ".join(f"{px:.2f},{py:.2f}" for px, py in points) + '" {paint}/>'


def _round_rect(x: float, y: float, w: float, h: float, adj: dict[str, int]) -> str:
    radius = min(w, h) * adj.get("adj", 16667) / 100000
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{radius:.2f}" '
        "{paint}/>"
    )


def _home_plate(x: float, y: float, w: float, h: float, adj: dict[str, int]) -> str:
    tip = min(w, h * adj.get("adj", 50000) / 100000)
    return _poly((x, y), (x + w - tip, y), (x + w, y + h / 2), (x + w - tip, y + h), (x, y + h))


def _chevron(x: float, y: float, w: float, h: float, adj: dict[str, int]) -> str:
    tip = min(w, h * adj.get("adj", 50000) / 100000)
    return _poly(
        (x, y),
        (x + w - tip, y),
        (x + w, y + h / 2),
        (x + w - tip, y + h),
        (x, y + h),
        (x + tip, y + h / 2),
    )


_PRESETS: dict[str, Callable[[float, float, float, float, dict[str, int]], str]] = {
    "rect": lambda x, y, w, h, _a: (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" {{paint}}/>'
    ),
    "roundRect": _round_rect,
    "ellipse": lambda x, y, w, h, _a: (
        f'<ellipse cx="{x + w / 2:.2f}" cy="{y + h / 2:.2f}" rx="{w / 2:.2f}" ry="{h / 2:.2f}" '
        "{paint}/>"
    ),
    "line": lambda x, y, w, h, _a: (
        f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x + w:.2f}" y2="{y + h:.2f}" {{paint}}/>'
    ),
    "straightConnector1": lambda x, y, w, h, _a: (
        f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x + w:.2f}" y2="{y + h:.2f}" {{paint}}/>'
    ),
    "triangle": lambda x, y, w, h, a: _poly(
        (x + w * a.get("adj", 50000) / 100000, y), (x + w, y + h), (x, y + h)
    ),
    "rtTriangle": lambda x, y, w, h, _a: _poly((x, y), (x + w, y + h), (x, y + h)),
    "diamond": lambda x, y, w, h, _a: _poly(
        (x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)
    ),
    "parallelogram": lambda x, y, w, h, a: _poly(
        (x + min(w, h * a.get("adj", 25000) / 100000), y),
        (x + w, y),
        (x + w - min(w, h * a.get("adj", 25000) / 100000), y + h),
        (x, y + h),
    ),
    "homePlate": _home_plate,
    "chevron": _chevron,
}


def _custom(geometry: Any, box: tuple[float, float, float, float]) -> str | None:
    """A custom geometry's paths, each scaled from its own w x h to the shape's box."""
    x, y, w, h = box
    out = []
    for path in geometry.iter(f"{_A}path"):
        pw, ph = int(path.get("w", 0)) or 1, int(path.get("h", 0)) or 1
        sx, sy = (w / pw if path.get("w") else 1 / 9525), (h / ph if path.get("h") else 1 / 9525)

        def point(node: Any, sx: float = sx, sy: float = sy) -> tuple[float, float]:
            return x + int(node.get("x", 0)) * sx, y + int(node.get("y", 0)) * sy

        commands = []
        current = (x, y)
        for step in path:
            kind = _tag(step)
            points = [point(pt) for pt in step.iter(f"{_A}pt")]
            if kind == "moveTo" and points:
                current = points[0]
                commands.append(f"M{current[0]:.2f},{current[1]:.2f}")
            elif kind == "lnTo" and points:
                current = points[0]
                commands.append(f"L{current[0]:.2f},{current[1]:.2f}")
            elif kind == "cubicBezTo" and len(points) == 3:
                current = points[2]
                commands.append("C" + " ".join(f"{px:.2f},{py:.2f}" for px, py in points))
            elif kind == "quadBezTo" and len(points) == 2:
                current = points[1]
                commands.append("Q" + " ".join(f"{px:.2f},{py:.2f}" for px, py in points))
            elif kind == "arcTo":
                current, arc = _arc(step, current, sx, sy)
                commands.append(arc)
            elif kind == "close":
                commands.append("Z")
        if commands:
            filled = "" if path.get("fill") != "none" else ' fill-opacity="0"'
            out.append(f'<path d="{" ".join(commands)}"{filled} {{paint}}/>')
    return "".join(out) or None


def _arc(step: Any, start: tuple[float, float], sx: float, sy: float) -> tuple[Any, str]:
    """DrawingML's arcTo (radii, start angle, swing) as an SVG elliptical arc."""
    wr, hr = int(step.get("wR", 0)) * sx, int(step.get("hR", 0)) * sy
    begin = math.radians(int(step.get("stAng", 0)) / 60000)
    swing = math.radians(int(step.get("swAng", 0)) / 60000)
    cx, cy = start[0] - wr * math.cos(begin), start[1] - hr * math.sin(begin)
    end = (cx + wr * math.cos(begin + swing), cy + hr * math.sin(begin + swing))
    large = 1 if abs(swing) > math.pi else 0
    sweep = 1 if swing > 0 else 0
    return end, f"A{wr:.2f},{hr:.2f} 0 {large} {sweep} {end[0]:.2f},{end[1]:.2f}"


def _plain_colour(slot: Any) -> str | None:
    for node in slot:
        if _tag(node) == "srgbClr":
            return str(node.get("val"))
        if _tag(node) == "sysClr" and node.get("lastClr"):
            return str(node.get("lastClr"))
    return None


def _modified(base: str, node: Any) -> str:
    """`base` (RRGGBB) with the node's lumMod, lumOff, tint, shade and alpha applied."""
    r, g, b = (int(base[i : i + 2], 16) / 255 for i in (0, 2, 4))
    alpha = 1.0
    for mod in node:
        kind, value = _tag(mod), int(mod.get("val", 0)) / 100000
        if kind in ("lumMod", "lumOff"):
            hue, light, sat = colorsys.rgb_to_hls(r, g, b)
            light = light * value if kind == "lumMod" else light + value
            r, g, b = colorsys.hls_to_rgb(hue, min(max(light, 0.0), 1.0), sat)
        elif kind == "tint":
            r, g, b = (c + (1 - c) * (1 - value) for c in (r, g, b))
        elif kind == "shade":
            r, g, b = (c * value for c in (r, g, b))
        elif kind == "alpha":
            alpha = value
    rgb = "".join(f"{round(min(max(c, 0.0), 1.0) * 255):02X}" for c in (r, g, b))
    if alpha >= 1:
        return f"#{rgb}"
    return f"rgba({int(rgb[0:2], 16)},{int(rgb[2:4], 16)},{int(rgb[4:6], 16)},{alpha:.3f})"


def _image_uri(part: Any, rel_id: str) -> str | None:
    if not rel_id or rel_id not in part.rels:
        return None
    target = part.rels[rel_id].target_part
    kind = _IMAGE_TYPES.get(str(target.partname).rsplit(".", 1)[-1].lower())
    if kind is None:
        return None
    return f"data:{kind};base64,{base64.b64encode(target.blob).decode()}"
