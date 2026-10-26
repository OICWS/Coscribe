"""The components of a spec written as Word content (decision 0024): a cover, a row of figures, a
call-out, a picture with its caption. Each is the OOXML a person would build by hand (a shaded
one-cell table for a bar or a call-out), tied to the theme's colours, and carries a bookmark named
`cs_<component>` so the editor can tell what it was when it reads the file back.

Written as XML strings, in schema order, rather than through python-docx's paragraph and table
properties: the result is the same on every machine and the validator reads it the same way."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from ..markdown_blocks import parse_inline_runs
from ._style import ACCENT
from ._xml import _docx_text_width_pt

GREY = "7F7F7F"
# kind -> (strong colour, tint)
CALLOUT_COLOURS = {
    "info": ("2E75B6", "EAF2FA"),
    "success": ("2E8B57", "E8F5EC"),
    "warn": ("D98A00", "FFF4DC"),
    "danger": ("C0392B", "FCEBE9"),
}
_GREEN, _RED = "2E8B57", "C0392B"
_UP = ("+", "▲", "↑")
_DOWN = ("-", "−", "▼", "↓")
_TOC_HEADING_ID = "TOCHeading"


def _tint(hex6: str, strength: float = 0.9) -> str:
    """The colour mixed towards white; `strength` is how much white."""
    channels = [int(hex6[i : i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(c + (255 - c) * strength):02X}" for c in channels)


def _element(xml: str) -> Any:
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    return parse_xml(re.sub(r"^<([\w:]+)", rf"<\1 {nsdecls('w')}", xml, count=1))


def _add(document: Any, element: Any) -> None:
    document.element.body.insert_element_before(element, "w:sectPr")


def _run(text: str, *, size: float, colour: str, bold: bool = False, italic: bool = False) -> str:
    props = ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "")
    props += f'<w:color w:val="{colour}"/><w:sz w:val="{round(size * 2)}"/>'
    return f'<w:r><w:rPr>{props}</w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _inline(text: str, *, size: float, colour: str) -> str:
    """The text with its `**bold**` and `*italic*` as runs."""
    return "".join(
        _run(part, size=size, colour=colour, bold=bold, italic=italic)
        for part, bold, italic in parse_inline_runs(text)
    )


def _paragraph(
    runs: str = "",
    *,
    style: str = "",
    before: float = 0,
    after: float = 0,
    border: str = "",
    right_indent: float = 0,
    centre: bool = False,
    mark: str = "",
) -> str:
    """A `w:p` with its properties in schema order; `mark` is a bookmark at the head of it."""
    props = f'<w:pStyle w:val="{style}"/>' if style else ""
    props += border
    props += f'<w:spacing w:before="{round(before * 20)}" w:after="{round(after * 20)}"/>'
    if right_indent:
        props += f'<w:ind w:right="{round(right_indent * 20)}"/>'
    if centre:
        props += '<w:jc w:val="center"/>'
    return f"<w:p><w:pPr>{props}</w:pPr>{mark}{runs}</w:p>"


def _bookmark(document: Any, name: str) -> str:
    """A bookmark around nothing, to stand at the head of the paragraph it names."""
    ident = 900 + int(document.element.body.xpath("count(.//w:bookmarkStart)")) + 1
    return f'<w:bookmarkStart w:id="{ident}" w:name="cs_{name}"/><w:bookmarkEnd w:id="{ident}"/>'


def _mark_run(document: Any, run: Any, name: str) -> None:
    """A bookmark around a run that is not made of the paragraph XML above (a picture, a chart)."""
    start, end = (_element(tag) for tag in re.findall(r"<[^>]+/>", _bookmark(document, name)))
    run.addprevious(start)
    run.addnext(end)


def _cell(
    width_pt: float,
    paragraphs: str,
    *,
    fill: str | None,
    left: tuple[str, int] | None = None,
    sides: tuple[str, int] | None = None,
) -> str:
    """A table cell with no border but the ones named: `left`, and `sides` (left and right)."""

    def edge(name: str, spec: tuple[str, int] | None) -> str:
        if spec is None:
            return f'<w:{name} w:val="nil"/>'
        return f'<w:{name} w:val="single" w:sz="{spec[1]}" w:space="0" w:color="{spec[0]}"/>'

    borders = edge("top", None) + edge("left", left or sides) + edge("bottom", None)
    borders += edge("right", sides)
    shade = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
    margins = "".join(
        f'<w:{side} w:w="{w}" w:type="dxa"/>'
        for side, w in (("top", 100), ("left", 180), ("bottom", 100), ("right", 180))
    )
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{round(width_pt * 20)}" w:type="dxa"/>'
        f"<w:tcBorders>{borders}</w:tcBorders>{shade}<w:tcMar>{margins}</w:tcMar></w:tcPr>"
        f"{paragraphs}</w:tc>"
    )


def _table(document: Any, cells: list[str], widths: list[float], *, height_pt: float = 0) -> None:
    """A one-row, fixed-width table of the given cells, appended to the body."""
    row_props = "<w:cantSplit/>"
    if height_pt:
        row_props += f'<w:trHeight w:val="{round(height_pt * 20)}" w:hRule="exact"/>'
    grid = "".join(f'<w:gridCol w:w="{round(w * 20)}"/>' for w in widths)
    row = f"<w:tr><w:trPr>{row_props}</w:trPr>{''.join(cells)}</w:tr>"
    table = (
        f'<w:tbl><w:tblPr><w:tblW w:w="{round(sum(widths) * 20)}" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/><w:tblLook w:val="0000"/></w:tblPr>'
        f"<w:tblGrid>{grid}</w:tblGrid>{row}</w:tbl>"
    )
    _add(document, _element(table))


def _spacer(document: Any) -> None:
    """A table is followed by a paragraph: two tables back to back would join into one."""
    _add(document, _element(_paragraph()))


def add_cover(document: Any, head: dict[str, Any], style: str) -> None:
    """The cover page: a colour band (style `band`), the title, an accent rule, the subtitle and
    the author and date, then a page break."""
    width = _docx_text_width_pt(document)
    if style == "band":
        band = _paragraph(mark=_bookmark(document, "cover"))
        _table(document, [_cell(width, band, fill=ACCENT)], [width], height_pt=22)
    top = 110 if style == "band" else 90
    title = _run(str(head["title"]), size=22, colour=ACCENT)
    _add(document, _element(_paragraph(title, style="Title", before=top)))
    line = f'<w:pBdr><w:bottom w:val="single" w:sz="18" w:space="6" w:color="{ACCENT}"/></w:pBdr>'
    _add(document, _element(_paragraph(after=8, border=line, right_indent=width * 0.6)))
    if head.get("subtitle"):
        subtitle = _run(str(head["subtitle"]), size=14, colour=GREY)
        _add(document, _element(_paragraph(subtitle, after=4)))
    for key in ("author", "date"):
        if head.get(key):
            text = _run(str(head[key]), size=10.5, colour=GREY)
            _add(document, _element(_paragraph(text, before=6 if key == "author" else 0)))
    document.add_page_break()


def _delta_colour(delta: str) -> str:
    if delta.startswith(_UP):
        return _GREEN
    if delta.startswith(_DOWN):
        return _RED
    return GREY


def add_stats(document: Any, body: str) -> None:
    """A row of figures, each a card: `label | value | change` per line, two to four lines."""
    rows = [[p.strip() for p in line.split("|")] for line in body.splitlines() if line.strip()]
    if not 2 <= len(rows) <= 4 or any(len(r) < 2 for r in rows):
        raise ValueError(
            "stats has two to four lines, each `label | value | change` (change optional)"
        )
    width = _docx_text_width_pt(document)
    cells = []
    for index, parts in enumerate(rows):
        label, value = parts[0], parts[1]
        change = parts[2] if len(parts) > 2 else ""
        mark = _bookmark(document, "stats") if index == 0 else ""
        content = _paragraph(_run(label, size=9, colour=GREY), after=2, mark=mark)
        content += _paragraph(_run(value, size=20, colour=ACCENT, bold=True), after=2)
        if change:
            content += _paragraph(_run(change, size=9, colour=_delta_colour(change)))
        cells.append(_cell(width / len(rows), content, fill=_tint(ACCENT), sides=("FFFFFF", 36)))
    _table(document, cells, [width / len(rows)] * len(rows))
    _spacer(document)


def add_callout(document: Any, kind: str, body: str) -> None:
    """A shaded block with a bar down its left edge, for what the reader must not miss."""
    strong, tint = CALLOUT_COLOURS[kind]
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    paragraphs = ""
    for index, line in enumerate(lines):
        text = "• " + line[2:] if line.startswith(("- ", "* ")) else line
        mark = _bookmark(document, f"callout_{kind}") if index == 0 else ""
        after = 3 if index < len(lines) - 1 else 0
        paragraphs += _paragraph(_inline(text, size=10, colour="262626"), after=after, mark=mark)
    width = _docx_text_width_pt(document)
    _table(document, [_cell(width, paragraphs, fill=tint, left=(strong, 24))], [width])
    _spacer(document)


def add_figure(document: Any, args: str, caption: str, resolve: Callable[[str], Path]) -> None:
    """A picture centred on its own line, with its caption below."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    if not args:
        raise ValueError("figure names an image: `:::figure images/chart.png`")
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    width = Pt(_docx_text_width_pt(document) * 0.85)
    paragraph.add_run().add_picture(str(resolve(args)), width=width)
    _mark_run(document, paragraph.runs[0].element, "figure")
    if caption:
        text = _paragraph(_inline(caption, size=9, colour=GREY), style="Caption", centre=True)
        _add(document, _element(text))


def add_contents_title(document: Any, cjk: bool) -> None:
    """The word above a contents list, in a style of its own so the list does not hold it."""
    styles = document.styles.element
    if not styles.xpath(f'w:style[@w:styleId="{_TOC_HEADING_ID}"]'):
        styles.append(
            _element(
                f'<w:style w:type="paragraph" w:customStyle="1" w:styleId="{_TOC_HEADING_ID}">'
                '<w:name w:val="TOC Heading"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                '<w:uiPriority w:val="39"/><w:qFormat/><w:pPr><w:spacing w:after="200"/></w:pPr>'
                f'<w:rPr><w:b/><w:color w:val="{ACCENT}"/><w:sz w:val="32"/></w:rPr></w:style>'
            )
        )
    label = _run("目录" if cjk else "Contents", size=16, colour=ACCENT, bold=True)
    _add(document, _element(_paragraph(label, style=_TOC_HEADING_ID, after=10)))


def add_chart(document: Any, args: str, body: str) -> None:
    """A native Word chart: `:::chart bar Title`, then the data as a pipe table (a category column
    and one column per series), then an optional `caption: ...` line."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches

    from ..._chart_data import CHART_TYPES, parse_chart_table
    from ..._docx_chart import add_chart_paragraph
    from ._xml import _text_column_emu

    kind, _, title = args.partition(" ")
    if kind not in CHART_TYPES:
        raise ValueError(
            f"chart is `chart <type> <title>`, the type one of: {', '.join(sorted(CHART_TYPES))}"
        )
    lines = body.splitlines()
    caption = next(
        (line.partition(":")[2].strip() for line in lines if line.startswith("caption:")), ""
    )
    data = "\n".join(line for line in lines if not line.startswith("caption:"))
    categories, series = parse_chart_table(data, "chart")
    if kind == "pie" and len(series) > 1:
        raise ValueError("a pie chart takes one data column besides the category column")
    paragraph = add_chart_paragraph(
        document,
        kind,
        categories,
        series,
        title.strip(),
        _text_column_emu(document),
        int(Inches(3.2)),
    )
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _mark_run(document, paragraph.runs[0].element, "chart")
    if caption:
        text = _paragraph(_inline(caption, size=9, colour=GREY), style="Caption", centre=True)
        _add(document, _element(text))
