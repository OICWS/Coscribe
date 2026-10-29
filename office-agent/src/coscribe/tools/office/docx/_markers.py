"""What an export asks of the writer through the markdown it hands over (decision 0025): a callout
framed in its colour, a chart drawn natively, a task item with its box. The subset cannot say
these, so the export leaves a marker paragraph and this pass, which sees the finished document,
does them."""

from __future__ import annotations

import re
from typing import Any

from ..._chart_data import CHART_TYPES, parse_chart_table
from ..._docx_chart import add_chart_paragraph
from ._style import EAST_ASIAN_FONT, LATIN_FONT

# The Doc panel's chart colours (frontend lib/docChart.ts), so the Word file looks like the Doc.
_CHART_COLOURS = ("4F6EF7", "12A88A", "F59F00", "E0508A", "8A63E8", "6B7280")

_CALLOUT = re.compile(r"§callout:(\w+):([^§]*)§")
_END = "§/callout§"
_CHART = re.compile(r"§chart:(\w+):([^§]*)§")
_RULE = "§rule§"
_BOXES = ("☐ ", "☑ ")

# The colours the Doc editor draws a callout in (index.css), so a page and its Word file agree.
_COLOURS = {
    "NOTE": "4F6EF7",
    "TIP": "12A88A",
    "IMPORTANT": "8A63E8",
    "WARNING": "D98A00",
    "CAUTION": "D6443F",
}

# Children of w:pPr in schema order; the writer rejects a file whose children are out of it.
_PPR_ORDER = (
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
    "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
    "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
    "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
    "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr",
    "sectPr", "pPrChange",
)  # fmt: skip


def _put(ppr: Any, element: Any) -> None:
    """Add `element` to a paragraph's properties where the schema wants it, replacing its twin."""
    name = element.tag.rsplit("}", 1)[1]
    for old in ppr.findall(element.tag):
        ppr.remove(old)
    later = set(_PPR_ORDER[_PPR_ORDER.index(name) + 1 :])
    for child in ppr:
        if child.tag.rsplit("}", 1)[1] in later:
            child.addprevious(element)
            return
    ppr.append(element)


def _make(tag: str, **attributes: str) -> Any:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    element = OxmlElement(tag)
    for key, value in attributes.items():
        element.set(qn(f"w:{key}"), value)
    return element


def _tint(colour: str) -> str:
    """The colour at 9% over white, as the editor's callout is."""
    channels = (int(colour[i : i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{round(c * 0.09 + 255 * 0.91):02X}" for c in channels)


def _frame(paragraph: Any, colour: str, *, before: int, after: int, last: bool) -> None:
    ppr = paragraph._p.get_or_add_pPr()
    if not last:
        # A callout is not split from its label, nor one paragraph from the next, across a page.
        _put(ppr, _make("w:keepNext"))
    border = _make("w:pBdr")
    border.append(_make("w:left", val="single", sz="24", space="8", color=colour))
    _put(ppr, border)
    _put(ppr, _make("w:shd", val="clear", color="auto", fill=_tint(colour)))
    _put(ppr, _make("w:spacing", before=str(before), after=str(after)))
    _put(ppr, _make("w:ind", left="170"))


def _paragraph(element: Any, document: Any) -> Any:
    from docx.text.paragraph import Paragraph

    return Paragraph(element, document._body)


def _is_paragraph(element: Any) -> bool:
    return bool(element.tag.endswith("}p"))


def _callout(document: Any, start: Any, end: Any, kind: str, label: str) -> None:
    from docx.shared import Pt, RGBColor

    colour = _COLOURS.get(kind.upper(), _COLOURS["NOTE"])
    inside = []
    for element in start.itersiblings():
        if element is end:
            break
        if _is_paragraph(element):
            inside.append(_paragraph(element, document))

    head = _paragraph(start, document)
    for run in list(head.runs):
        run._r.getparent().remove(run._r)
    run = head.add_run(label.upper())
    run.bold = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor.from_string(colour)
    _frame(head, colour, before=120, after=20, last=not inside)
    for index, paragraph in enumerate(inside):
        last = index == len(inside) - 1
        _frame(paragraph, colour, before=0, after=120 if last else 60, last=last)
    end.getparent().remove(end)


def _chart(document: Any, marker: Any, table: Any, kind: str, title: str) -> bool:
    """Replace the marker and the table after it with a native chart; False if it has no data."""
    from docx.shared import Inches
    from docx.table import Table

    rows = [[cell.text.strip() for cell in row.cells] for row in Table(table, document._body).rows]
    if kind not in CHART_TYPES or len(rows) < 2:
        return False
    ruled = rows[:1] + [["---"] * len(rows[0])] + rows[1:]
    text = "\n".join("| " + " | ".join(row) + " |" for row in ruled)
    try:
        categories, series = parse_chart_table(text, "export")
    except ValueError:
        return False
    if kind == "pie" and len(series) > 1:
        return False
    section = document.sections[0]
    width = int(section.page_width - section.left_margin - section.right_margin)
    paragraph = add_chart_paragraph(
        document,
        kind,
        categories,
        series,
        title,
        width,
        int(Inches(3.2)),
        (document.styles["Normal"].font.name or LATIN_FONT, EAST_ASIAN_FONT),
        _CHART_COLOURS,
    )
    marker.addprevious(paragraph._p)
    marker.getparent().remove(marker)
    table.getparent().remove(table)
    return True


def _title_only(document: Any, marker: Any, title: str) -> None:
    """A chart that cannot be drawn keeps its title over the table that stays."""
    paragraph = _paragraph(marker, document)
    for run in list(paragraph.runs):
        run._r.getparent().remove(run._r)
    paragraph.add_run(title or "Chart").bold = True


def _rule(paragraph: Any) -> None:
    """A horizontal rule: an empty line with a hairline under it."""
    for run in list(paragraph.runs):
        run._r.getparent().remove(run._r)
    ppr = paragraph._p.get_or_add_pPr()
    border = _make("w:pBdr")
    border.append(_make("w:bottom", val="single", sz="6", space="1", color="BFBFBF"))
    _put(ppr, border)
    _put(ppr, _make("w:spacing", before="60", after="120"))


def _boxed(paragraph: Any) -> None:
    """A task item stands without a bullet, its box in front."""
    ppr = paragraph._p.get_or_add_pPr()
    numbering = _make("w:numPr")
    numbering.append(_make("w:ilvl", val="0"))
    numbering.append(_make("w:numId", val="0"))
    _put(ppr, numbering)
    _put(ppr, _make("w:ind", left="360", hanging="360"))


def apply_markers(document: Any) -> None:
    for element in list(document.element.body.iterchildren()):
        if element.getparent() is None or not _is_paragraph(element):
            continue
        paragraph = _paragraph(element, document)
        text = paragraph.text.strip()
        if callout := _CALLOUT.fullmatch(text):
            end = next(
                (
                    sibling
                    for sibling in element.itersiblings()
                    if _is_paragraph(sibling) and _paragraph(sibling, document).text.strip() == _END
                ),
                None,
            )
            if end is None:
                element.getparent().remove(element)
            else:
                _callout(document, element, end, callout[1], callout[2])
        elif text == _RULE:
            _rule(paragraph)
        elif chart := _CHART.fullmatch(text):
            table = element.getnext()
            is_table = table is not None and table.tag.endswith("}tbl")
            if not (is_table and _chart(document, element, table, chart[1], chart[2])):
                _title_only(document, element, chart[2])
        elif (
            paragraph.style is not None
            and paragraph.style.name.startswith("List")
            and text.startswith(_BOXES)
        ):
            _boxed(paragraph)
