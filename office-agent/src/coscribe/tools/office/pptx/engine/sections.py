"""Compile a deck's slide sections (positioned HTML, decision 0015) into a .pptx.

Text elements become text boxes that wrap in PowerPoint (`text_box`); shapes, pictures and
drawings are turned into the SVG page language and handed to the same emitter as the SVG pages,
scaled from the 1920-wide canvas, so they come out as the same native shapes. Errors are collected
per section, as for the pages, for the model to repair.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from lxml import etree
from pptx import Presentation
from pptx.util import Emu

from ...._native_svg.svg_to_pptx import geometry_properties, tspan_flattener
from ...._native_svg.svg_to_pptx.drawingml import elements, utils
from ...._native_svg.svg_to_pptx.drawingml.context import ConvertContext, ShapeResult
from ..animation import add_animation_step
from ..transitions import set_slide_transition
from . import section_objects
from .checker import check_deck
from .compiler import (
    EMU_PER_PX as SVG_EMU_PER_PX,
)
from .compiler import (
    NSDECL,
    PAGE_CHECKS,
    SVG_NS,
    TITLE_ID,
    CompileReport,
    PageReport,
    attach_relationships,
    convert_element,
    make_title_placeholder,
)
from .icons import expand_icons
from .section_format import (
    BUILD_INS,
    CANVAS,
    MIN_READABLE_PX,
    SHAPES,
    TEXT_TAGS,
    Section,
    SectionError,
    Style,
    TextElement,
    colour,
    label,
    local,
    parse_section,
    text_element,
)
from .template import layout
from .text_box import EMU_PER_PX, TextBox, text_box_xml
from .text_layout import text_height

_SCALE = EMU_PER_PX / SVG_EMU_PER_PX
# Text that needs this little more height than its box still fits: rounding, not overflow.
_TOLERANCE_PX = 2.0
_MAX_ELEMENTS = 200
_FIT = {"cover": "xMidYMid slice", "contain": "xMidYMid meet", "fill": "none"}
_SHIFT = {"t": 0.0, "ctr": 0.5, "b": 1.0}
_P = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
_TRANSITION_SECONDS = 0.7
_BUILD_MS = 500

# ("text", TextBox) or ("drawing", (the SVG element to convert, the scale it is drawn at))
Planned = tuple[str, Any]


def compile_sections(
    sections: Sequence[tuple[str, str]],
    out: Path,
    *,
    resource_root: Path | None = None,
    sections_dir: Path | None = None,
) -> CompileReport:
    """Write `out` from `(name, section_text)` pairs, one slide each, in order. A picture's
    path is resolved against `sections_dir`, the folder the sections are in. The deck is written
    even when sections have errors, so a preview can show what the repair has to fix."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = (Emu(v * EMU_PER_PX) for v in CANVAS)
    reports = []
    for name, text in sections:
        report = PageReport(name)
        reports.append(report)
        slide = prs.slides.add_slide(layout(prs, None))
        for placeholder in list(slide.placeholders):
            placeholder.element.getparent().remove(placeholder.element)
        try:
            section = parse_section(text)
        except SectionError as e:
            report.errors.append(str(e))
            continue
        _compile(slide, section, report, resource_root, sections_dir or resource_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return CompileReport(out, reports)


def check_sections(report: CompileReport, sources: Sequence[str] | None = None) -> None:
    """The SVG pages' checks over a compiled deck of sections, reported in the sections' px."""
    check_deck(report, sources, emu_per_px=EMU_PER_PX)


def _compile(
    slide: Any,
    section: Section,
    report: PageReport,
    resource_root: Path | None,
    folder: Path | None,
) -> None:
    if len(section.elements) > _MAX_ELEMENTS:
        report.errors.append(
            f"{len(section.elements)} elements: a slide holds {_MAX_ELEMENTS} at most"
        )
    drawing = ET.Element(f"{{{SVG_NS}}}svg", viewBox=f"0 0 {CANVAS[0]} {CANVAS[1]}")
    planned: list[Planned] = []
    build_ins: list[str | None] = []
    for elem, style in section.elements:
        try:
            planned.append(_plan(elem, style, section, drawing, report))
        except SectionError as e:
            report.errors.append(str(e))
            continue
        build_ins.append(BUILD_INS.get(elem.get("data-build-in", "")))
    ctx = _context(drawing, report, resource_root, folder)
    shapes, builds = [], []
    for (kind, item), build in zip(planned, build_ins, strict=True):
        if kind == "text":
            item.shape_id = ctx.next_id()
            shapes.append(text_box_xml(item))
        elif (result := _convert(item[0], item[1], ctx, report)) is not None:
            shapes.append(result.xml)
        else:
            continue
        builds.append(build)
    sp_tree = slide.shapes._spTree
    animated: list[tuple[Any, str]] = []
    for xml, build in zip(attach_relationships(slide, ctx, shapes, report), builds, strict=True):
        for i, element in enumerate(etree.fromstring(f"<p:wrap {NSDECL}>{xml}</p:wrap>")):
            sp_tree.append(element)
            report.shapes += 1
            if build and i == 0:
                animated.append((element, build))
    _finish(slide, section, report)
    _motion(slide, section.transition, animated)


def _plan(
    elem: ET.Element, style: Style, section: Section, drawing: ET.Element, report: PageReport
) -> Planned:
    tag = local(elem)
    if tag in TEXT_TAGS:
        return "text", _text(text_element(elem, style, section), report)
    scale = 1.0
    if tag == "x-shape":
        svg = _shape(elem, style)
    elif tag == "img":
        svg = _picture(elem, style)
    elif tag == "table":
        svg = section_objects.table(elem, style, _SCALE)
    elif tag == "x-chart":
        svg = section_objects.chart(elem, style, _SCALE)
    elif tag == "x-icon":
        svg = section_objects.icon(elem, style)
    else:
        svg, scale = _drawing(elem, style, drawing)
    drawing.append(svg)
    return "drawing", (svg, scale)


def _convert(
    svg: ET.Element, scale: float, ctx: ConvertContext, report: PageReport
) -> ShapeResult | None:
    """A drawing's scale is applied by the conversion, not by a transform: the page checks
    refuse a scaled group with text in it, which the emitter sizes per run instead."""
    if scale == 1.0:
        return convert_element(svg, ctx, report)
    child = ctx.child(sx=scale, sy=scale)
    result = convert_element(svg, child, report)
    ctx.sync_from_child(child)
    return result


def _text(element: TextElement, report: PageReport) -> TextBox:
    x, y, width, height = element.box
    inner = width - 2 * element.padding
    measured_width = float("inf") if element.nowrap else inner
    needed = text_height(element.paragraphs, measured_width, element.line_height)
    needed += 2 * element.padding
    if needed > height + _TOLERANCE_PX:
        report.errors.append(
            f"{element.label}: its text needs {needed:.0f} px of height and the box has "
            f"{height:.0f}: make the box taller or the text shorter or smaller"
        )
    small = min((r.font.size for p in element.paragraphs for r in p.runs), default=None)
    if small is not None and small < MIN_READABLE_PX:
        report.warnings.append(
            f"{element.label}: {small:.0f} px text is hard to read on a projected slide; "
            f"use {MIN_READABLE_PX:.0f} px or more unless it is a footnote"
        )
    anchor, fits = element.anchor, False
    if element.fill is None and needed < height:
        # Drawn to its text's height, so the checks and PowerPoint's selection see the text.
        y += (height - needed) * _SHIFT[anchor]
        height, anchor, fits = needed, "t", True
    return TextBox(
        shape_id=0,
        name=element.name or f"{element.tag} text",
        box=(x, y, width, height),
        paragraphs=element.paragraphs,
        bullets=element.bullets,
        align=element.align,
        anchor=anchor,
        line_height=element.line_height,
        padding=element.padding,
        fill=element.fill,
        fits_text=fits,
        nowrap=element.nowrap,
    )


def _shape(elem: ET.Element, style: Style) -> ET.Element:
    kind = elem.get("data-shape", "rect")
    if kind not in SHAPES:
        raise SectionError(f"{label(elem)}: data-shape is one of {', '.join(SHAPES)}")
    if len(elem) or (elem.text or "").strip():
        raise SectionError(f"{label(elem)} holds no text; put a <p> over it")
    x, y, w, h = style.box()
    paint = _paint(elem, style, kind == "line")
    if kind == "rect":
        return _svg("rect", paint, x=x, y=y, width=w, height=h)
    if kind == "round-rect":
        radius = style.px("border-radius", round(min(w, h) * 0.12))
        return _svg("rect", paint, x=x, y=y, width=w, height=h, rx=radius)
    if kind == "ellipse":
        return _svg("ellipse", paint, cx=x + w / 2, cy=y + h / 2, rx=w / 2, ry=h / 2)
    if kind == "line":
        return _svg("line", paint, x1=x, y1=y, x2=x + w, y2=y + h)
    if kind == "triangle":
        points = [(x + w / 2, y), (x + w, y + h), (x, y + h)]
    else:
        head, shaft = min(h, w / 2), h * 0.3
        points = [
            (x, y + shaft),
            (x + w - head, y + shaft),
            (x + w - head, y),
            (x + w, y + h / 2),
            (x + w - head, y + h),
            (x + w - head, y + h - shaft),
            (x, y + h - shaft),
        ]
    paint["points"] = " ".join(f"{px:g},{py:g}" for px, py in points)
    return _svg("polygon", paint)


def _paint(elem: ET.Element, style: Style, line: bool) -> dict[str, str]:
    fill = None if line else style.colour("background")
    paint = {"fill": f"#{fill}" if fill else "none"}
    border = style.values.get("border", "none").strip()
    if border != "none":
        match = re.fullmatch(r"(\d+(?:\.\d+)?)px\s+(solid|dashed)\s+(#\w+)", border)
        if match is None:
            raise SectionError(f'{label(elem)}: border is "2px solid #RRGGBB" or "none"')
        width, dash, stroke = match.groups()
        paint["stroke"] = f"#{colour(stroke, f'{label(elem)}: border')}"
        paint["stroke-width"] = width
        if dash == "dashed":
            paint["stroke-dasharray"] = f"{float(width) * 3:g} {float(width) * 2:g}"
    elif line:
        raise SectionError(f"{label(elem)}: a line needs a border, which draws it")
    if "opacity" in style.values:
        paint["opacity"] = style.values["opacity"]
    if elem.get("id"):
        paint["id"] = elem.get("id", "")
    return paint


def _picture(elem: ET.Element, style: Style) -> ET.Element:
    x, y, w, h = style.box()
    fit = style.values.get("object-fit", "cover")
    if fit not in _FIT:
        raise SectionError(f"{label(elem)}: object-fit is one of {', '.join(_FIT)}")
    attrs = {"href": elem.get("src", ""), "preserveAspectRatio": _FIT[fit]}
    if elem.get("id"):
        attrs["id"] = elem.get("id", "")
    return _svg("image", attrs, x=x, y=y, width=w, height=h)


def _drawing(elem: ET.Element, style: Style, drawing: ET.Element) -> tuple[ET.Element, float]:
    """An embedded SVG, placed in its box as the browser does (`meet`: whole, centred)."""
    x, y, w, h = style.box()
    view = [float(v) for v in (elem.get("viewBox") or "").replace(",", " ").split()]
    if len(view) != 4 or view[2] <= 0 or view[3] <= 0:
        raise SectionError(f'{label(elem)} needs viewBox="0 0 W H"')
    scale = min(w / view[2], h / view[3])
    dx = x + (w - view[2] * scale) / 2 - view[0] * scale
    dy = y + (h - view[3] * scale) / 2 - view[1] * scale
    group = ET.Element(f"{{{SVG_NS}}}g", transform=f"translate({dx / scale:g} {dy / scale:g})")
    if elem.get("id"):
        group.set("id", elem.get("id", ""))
    for child in list(elem):
        child = _in_svg_namespace(child)
        (drawing if local(child) == "defs" else group).append(child)
    return group, scale


def _in_svg_namespace(elem: ET.Element) -> ET.Element:
    for node in elem.iter():
        if isinstance(node.tag, str) and not node.tag.startswith("{"):
            node.tag = f"{{{SVG_NS}}}{node.tag}"
    return elem


def _svg(tag: str, attrs: dict[str, str], **geometry: float) -> ET.Element:
    values = {k: f"{v:g}" for k, v in geometry.items()}
    return ET.Element(f"{{{SVG_NS}}}{tag}", {**values, **attrs})


def _context(
    drawing: ET.Element, report: PageReport, resource_root: Path | None, folder: Path | None
) -> ConvertContext:
    """The checks and preparation the SVG pages get, run over every drawn element at once."""
    report.errors.extend(expand_icons(drawing))
    try:
        geometry_properties.materialize_inline_geometry_properties(drawing)
    except Exception as e:  # reported to the model, not raised
        report.errors.append(f"inline geometry: {e}")
    for check in PAGE_CHECKS:
        report.errors.extend(check(drawing))
    if folder is not None:
        report.errors.extend(
            elements.project_image_errors(drawing, folder, resource_root=resource_root)
        )
    tspan_flattener.flatten_positional_tspans(
        ET.ElementTree(drawing), merge_paragraphs=True, preserve_line_breaks=True
    )
    defs, _duplicates = utils.project_definition_index(drawing)
    return ConvertContext(
        defs=defs,
        svg_dir=folder,
        resource_root=resource_root,
        inherited_styles=utils._extract_inheritable_styles(drawing),
        scale_x=_SCALE,
        scale_y=_SCALE,
        viewport_width=float(CANVAS[0]),
        viewport_height=float(CANVAS[1]),
        # As for the pages: an unmapped relationship then points nowhere instead of elsewhere.
        rel_id_counter=1000,
    )


def _motion(slide: Any, transition: str | None, animated: list[tuple[Any, str]]) -> None:
    """The slide's transition, then its build-ins, one click each in the section's order: the
    transition must come first, since the schema puts it before the timing tree."""
    if transition is not None:
        set_slide_transition(slide._element, transition, _TRANSITION_SECONDS)
    for element, effect in animated:
        add_animation_step(
            slide._element, _shape_id(element), effect, _BUILD_MS, "on-click", 0, None
        )
    if animated:
        _build_list(slide._element.find(f"{{{_P['p']}}}timing"), animated)


def _build_list(timing: Any, animated: list[tuple[Any, str]]) -> None:
    """How each animated object builds, as PowerPoint writes it: a chart or table as one piece
    (`bldGraphic`), a text box by its text (`bldP`)."""
    builds = etree.SubElement(timing, f"{{{_P['p']}}}bldLst")
    for element, _effect in animated:
        spid = str(_shape_id(element))
        kind = etree.QName(element).localname
        if kind == "graphicFrame":
            graphic = etree.SubElement(builds, f"{{{_P['p']}}}bldGraphic", spid=spid, grpId="0")
            etree.SubElement(graphic, f"{{{_P['p']}}}bldAsOne")
        elif kind == "sp" and element.find(f"{{{_P['p']}}}txBody") is not None:
            etree.SubElement(builds, f"{{{_P['p']}}}bldP", spid=spid, grpId="0")
    if not len(builds):
        timing.remove(builds)


def _shape_id(element: Any) -> int:
    return int(element.xpath(".//p:cNvPr/@id", namespaces=_P)[0])


def _finish(slide: Any, section: Section, report: PageReport) -> None:
    sp_tree = slide.shapes._spTree
    if section.background is not None:
        background = etree.fromstring(
            f'<p:bg {NSDECL}><p:bgPr><a:solidFill><a:srgbClr val="{section.background}"/>'
            "</a:solidFill><a:effectLst/></p:bgPr></p:bg>"
        )
        slide._element.cSld.insert(0, background)
    if sp_tree.xpath(f'.//p:sp[p:nvSpPr/p:cNvPr/@name="{TITLE_ID}"][p:txBody]'):
        make_title_placeholder(sp_tree, report)
    else:
        report.warnings.append('no text with id="title": the slide has no title for the outline')
    if section.notes:
        slide.notes_slide.notes_text_frame.text = "\n".join(section.notes)
