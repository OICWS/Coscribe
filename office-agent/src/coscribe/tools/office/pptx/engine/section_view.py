"""A slide section drawn as one SVG, for the Slides panel's thumbnails, Present and downloads.

Shapes, pictures and drawings are the SVG the compiler hands to the emitter; text is laid out in
lines as the checks measure it (`text_layout.lines`), since an image has no text flow of its own.
Lines can differ from PowerPoint's by a word where the estimated advances are off; the editor
draws the slide being edited with the browser's own text instead.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from .compiler import SVG_NS, PageReport
from .section_format import CANVAS, SectionError, parse_section
from .sections import _plan
from .text_box import TextBox
from .text_layout import NORMAL_LINE_HEIGHT, Paragraph, Run, lines, text_height

_S = f"{{{SVG_NS}}}"
# Where the baseline sits in a line, as a share of the font size below the line's middle: about
# where the default faces put it.
_BASELINE = 0.36
_ANCHOR = {"l": "start", "just": "start", "ctr": "middle", "r": "end"}
_SHIFT = {"t": 0.0, "ctr": 0.5, "b": 1.0}


def section_drawing(text: str) -> ET.Element:
    """The section `text` as an SVG element on the 1920 x 1080 canvas, in the section's order.
    Charts and tables are left as their native markers and icons as `<use>`, for the caller to
    draw from the built slide; an element the compiler would refuse is left out. Raises
    `SectionError` for a section that cannot be read at all."""
    section = parse_section(text)
    root = ET.Element(
        f"{_S}svg",
        {
            "viewBox": f"0 0 {CANVAS[0]} {CANVAS[1]}",
            "width": str(CANVAS[0]),
            "height": str(CANVAS[1]),
            "font-family": section.font,
        },
    )
    ET.SubElement(
        root,
        f"{_S}rect",
        {"width": "100%", "height": "100%", "fill": f"#{section.background or 'FFFFFF'}"},
    )
    report = PageReport("view")
    for elem, style in section.elements:
        try:
            kind, item = _plan(elem, style, section, root, report)
        except SectionError:
            continue
        if kind == "text":
            root.append(_text_group(item))
        elif item[1] != 1.0:
            svg, scale = item
            svg.set("transform", f"scale({scale:g}) {svg.get('transform', '')}".strip())
    return root


def _text_group(box: TextBox) -> ET.Element:
    x, y, width, height = box.box
    group = ET.Element(f"{_S}g")
    if box.fill:
        ET.SubElement(
            group,
            f"{_S}rect",
            _num(x=x, y=y, width=width, height=height) | {"fill": f"#{box.fill}"},
        )
    inner = width - 2 * box.padding
    spacing = box.line_height or NORMAL_LINE_HEIGHT
    used = text_height(box.paragraphs, float("inf") if box.nowrap else inner, box.line_height)
    top = y + box.padding + (height - 2 * box.padding - used) * _SHIFT[box.anchor]
    for number, paragraph in enumerate(box.paragraphs, start=1):
        if number > 1:
            top += paragraph.space_before
        pitch = paragraph.size * spacing
        broken = [_one_line(paragraph)] if box.nowrap else lines(paragraph, inner)
        left = x + box.padding
        if box.bullets:
            marker = "•" if box.bullets == "bullet" else f"{number}."
            first = paragraph.runs[0] if paragraph.runs else None
            group.append(_line(left, top, pitch, "start", [(marker, first)] if first else []))
        for line in broken:
            anchor = _ANCHOR[box.align]
            at = {
                "start": left + paragraph.indent,
                "middle": left + paragraph.indent + (inner - paragraph.indent) / 2,
                "end": left + inner,
            }[anchor]
            group.append(_line(at, top, pitch, anchor, line))
            top += pitch
    return group


def _one_line(paragraph: Paragraph) -> list[tuple[str, Run]]:
    return [(run.text, run) for run in paragraph.runs]


def _line(
    x: float, top: float, pitch: float, anchor: str, pieces: list[tuple[str, Run]]
) -> ET.Element:
    size = max((run.font.size for _text, run in pieces), default=0.0)
    text = ET.Element(
        f"{_S}text",
        _num(x=x, y=top + pitch / 2 + size * _BASELINE) | {"text-anchor": anchor},
    )
    text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for words, run in pieces:
        span = ET.SubElement(text, f"{_S}tspan", _run_attributes(run))
        span.text = words.replace("\n", " ")
    return text


def _run_attributes(run: Run) -> dict[str, str]:
    font = run.font
    attributes = {
        "font-family": font.family,
        "font-size": f"{font.size:g}",
        "fill": f"#{run.colour}",
    }
    if font.bold:
        attributes["font-weight"] = "700"
    if font.italic:
        attributes["font-style"] = "italic"
    if font.tracking:
        attributes["letter-spacing"] = f"{font.tracking:g}"
    if run.underline:
        attributes["text-decoration"] = "underline"
    return attributes


def _num(**values: float) -> dict[str, Any]:
    return {name: f"{value:g}" for name, value in values.items()}
