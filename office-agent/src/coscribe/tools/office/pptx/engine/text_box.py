"""A section's text element as a PowerPoint text box that wraps, as it does in the browser.

The SVG pages' text boxes never wrap (each line is placed by the page); a section's box has a
width and PowerPoint breaks the lines, so the user can edit a paragraph in PowerPoint and it
reflows. Line spacing is exact (not a multiple of the font's own height) because that is the only
spacing whose height can be known here, and so checked against the box.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from xml.sax.saxutils import escape

from ...._native_svg.svg_to_pptx.drawingml.utils import is_cjk_char, parse_font_family
from .text_layout import Paragraph, Run

# The section canvas is 1920 px wide on a 13.333 in (12,192,000 EMU) slide.
EMU_PER_PX = 6350
_CENTIPOINTS_PER_PX = 50  # 1 px = 0.5 pt


@dataclass
class TextBox:
    shape_id: int
    name: str
    box: tuple[float, float, float, float]  # x, y, width, height in px
    paragraphs: Sequence[Paragraph]
    bullets: str | None  # None, "bullet" or "number"
    align: str  # l, ctr, r, just
    anchor: str  # t, ctr, b
    line_height: float
    padding: float = 0.0
    fill: str | None = None
    # A box drawn to its text's height grows with its text when edited in PowerPoint.
    fits_text: bool = False


def text_box_xml(box: TextBox) -> str:
    x, y, w, h = (round(v * EMU_PER_PX) for v in box.box)
    inset = round(box.padding * EMU_PER_PX)
    fill = (
        f'<a:solidFill><a:srgbClr val="{box.fill}"/></a:solidFill>' if box.fill else "<a:noFill/>"
    )
    # A text body needs at least one paragraph, even an empty one.
    paragraphs = "".join(_paragraph(p, box, i) for i, p in enumerate(box.paragraphs)) or "<a:p/>"
    autofit = "<a:spAutoFit/>" if box.fits_text else "<a:noAutofit/>"
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{box.shape_id}" name="{_attr(box.name)}"/>'
        '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{fill}</p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" lIns="{inset}" tIns="{inset}" rIns="{inset}" '
        f'bIns="{inset}" anchor="{box.anchor}" rtlCol="0">{autofit}</a:bodyPr>'
        f"<a:lstStyle/>{paragraphs}</p:txBody></p:sp>"
    )


def _paragraph(paragraph: Paragraph, box: TextBox, index: int) -> str:
    spacing = _points(paragraph.size * box.line_height)
    before = (
        f'<a:spcBef><a:spcPts val="{_points(paragraph.space_before)}"/></a:spcBef>'
        if index and paragraph.space_before
        else ""
    )
    indent = round(paragraph.indent * EMU_PER_PX)
    margins = f' marL="{indent}" indent="{-indent}"' if indent else ""
    first = paragraph.runs[0].font if paragraph.runs else None
    bullet = _bullet(box.bullets, first.family if first else "")
    runs = "".join(_runs(paragraph.runs))
    end = _run_properties(paragraph.runs[-1], "a:endParaRPr") if paragraph.runs else ""
    return (
        f'<a:p><a:pPr algn="{box.align}"{margins}><a:lnSpc><a:spcPts val="{spacing}"/></a:lnSpc>'
        f"{before}{bullet}</a:pPr>{runs}{end}</a:p>"
    )


def _bullet(kind: str | None, family: str) -> str:
    if kind == "bullet":
        return '<a:buFont typeface="Arial"/><a:buChar char="•"/>'
    if kind == "number":
        latin = parse_font_family(family)["latin"]
        return f'<a:buFont typeface="{_attr(latin)}"/><a:buAutoNum type="arabicPeriod"/>'
    return "<a:buNone/>"


def _runs(runs: Sequence[Run]) -> list[str]:
    out = []
    for run in runs:
        for i, part in enumerate(run.text.split("\n")):
            if i:
                out.append(f"<a:br>{_run_properties(run, 'a:rPr')}</a:br>")
            if part:
                out.append(f"<a:r>{_run_properties(run, 'a:rPr')}<a:t>{escape(part)}</a:t></a:r>")
    return out


def _run_properties(run: Run, tag: str) -> str:
    font = run.font
    faces = parse_font_family(font.family)
    lang = "zh-CN" if any(is_cjk_char(ch) for ch in run.text) else "en-US"
    flags = (' b="1"' if font.bold else "") + (' i="1"' if font.italic else "")
    flags += ' u="sng"' if run.underline else ""
    return (
        f'<{tag} lang="{lang}" sz="{_points(font.size)}"{flags} dirty="0">'
        f'<a:solidFill><a:srgbClr val="{run.colour}"/></a:solidFill>'
        f'<a:latin typeface="{_attr(faces["latin"])}"/><a:ea typeface="{_attr(faces["ea"])}"/>'
        f'<a:cs typeface="{_attr(faces["latin"])}"/></{tag}>'
    )


def _points(px: float) -> int:
    return round(px * _CENTIPOINTS_PER_PX)


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})
