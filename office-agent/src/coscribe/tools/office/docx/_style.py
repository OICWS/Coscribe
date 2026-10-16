"""The house style a new document gets when it is not built on the user's template."""

from __future__ import annotations

import re
from typing import Any

ACCENT = "1F4E79"
_HEADING_GREY = "262626"
_BORDER_GREY = "BFBFBF"
LATIN_FONT = "Calibri"
EAST_ASIAN_FONT = "Microsoft YaHei"
TABLE_STYLE_ID = "ReportTable"
_TABLE_STYLE_NAME = "Report Table"

_CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")
_TOTAL_LABEL = re.compile(
    r"^\s*(\*\*)?\s*(grand total|totals?|sum|合计|总计|小计|总额|共计)\b", re.IGNORECASE
)

# (level, size in pt, space before in pt, colour)
_HEADINGS = ((1, 16.0, 18.0, ACCENT), (2, 13.0, 14.0, ACCENT), (3, 11.5, 10.0, _HEADING_GREY))

A4_EMU = (7560310, 10692130)

# tblLook's legacy w:val bits, still read by Word before 2010.
_LOOK_FIRST_ROW = 0x0020
_LOOK_LAST_ROW = 0x0040
_LOOK_NO_H_BAND = 0x0200
_LOOK_NO_V_BAND = 0x0400


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def is_total_row(row: list[str]) -> bool:
    return bool(row) and bool(_TOTAL_LABEL.match(row[0]))


def apply_house_style(document: Any, *, cjk: bool) -> None:
    """Restyle a blank python-docx document: fonts, spacing, headings, a
    table style, A4 paper and a page-number footer. Spacing and fonts go into the
    document defaults rather than Normal, because a table style overrides
    the defaults but not a paragraph style: set on Normal, the body spacing
    would leak into every table cell."""
    from docx.oxml.ns import qn

    styles_element = document.styles.element
    defaults = styles_element.find(qn("w:docDefaults"))
    run_defaults = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    _set_fonts(run_defaults)
    size = "21" if cjk else "22"
    for tag in ("w:sz", "w:szCs"):
        run_defaults.find(qn(tag)).set(qn("w:val"), size)
    spacing = defaults.find(qn("w:pPrDefault")).find(qn("w:pPr")).find(qn("w:spacing"))
    spacing.set(qn("w:after"), "120")
    spacing.set(qn("w:line"), "276")
    spacing.set(qn("w:lineRule"), "auto")

    for level, size_pt, before_pt, colour in _HEADINGS:
        _style_heading(document.styles[f"Heading {level}"], size_pt, before_pt, colour)
    styles_element.append(_table_style_element())
    for section in document.sections:
        # python-docx's blank document is US Letter; A4 is the paper nearly everywhere else.
        section.page_width, section.page_height = A4_EMU
    _add_page_number_footer(document)


def _set_fonts(r_pr: Any) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    fonts = r_pr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, fonts)
    # A theme attribute wins over the explicit font on the same element.
    for theme in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        fonts.attrib.pop(qn(theme), None)
    fonts.set(qn("w:ascii"), LATIN_FONT)
    fonts.set(qn("w:hAnsi"), LATIN_FONT)
    fonts.set(qn("w:cs"), LATIN_FONT)
    fonts.set(qn("w:eastAsia"), EAST_ASIAN_FONT)


def _style_heading(style: Any, size_pt: float, before_pt: float, colour: str) -> None:
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    _set_fonts(style.element.get_or_add_rPr())
    style.font.size = Pt(size_pt)
    style.font.bold = True
    style.font.color.rgb = RGBColor.from_string(colour)
    # The blank document's heading styles already carry a w:spacing.
    spacing = style.element.get_or_add_pPr().find(qn("w:spacing"))
    spacing.set(qn("w:before"), str(round(before_pt * 20)))
    spacing.set(qn("w:after"), "120")


def _table_style_element() -> Any:
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    border = f'w:val="single" w:sz="4" w:space="0" w:color="{_BORDER_GREY}"'
    return parse_xml(
        f'<w:style {nsdecls("w")} w:type="table" w:customStyle="1" w:styleId="{TABLE_STYLE_ID}">'
        f'<w:name w:val="{_TABLE_STYLE_NAME}"/><w:basedOn w:val="TableNormal"/>'
        '<w:uiPriority w:val="59"/><w:qFormat/>'
        '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
        "<w:tblPr><w:tblBorders>"
        f"<w:top {border}/><w:left {border}/><w:bottom {border}/><w:right {border}/>"
        f"<w:insideH {border}/><w:insideV {border}/>"
        '</w:tblBorders><w:tblCellMar><w:top w:w="40" w:type="dxa"/>'
        '<w:left w:w="100" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/>'
        '<w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:bCs/><w:color w:val="FFFFFF"/></w:rPr>'
        f'<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="{ACCENT}"/></w:tcPr></w:tblStylePr>'
        '<w:tblStylePr w:type="lastRow"><w:rPr><w:b/><w:bCs/></w:rPr>'
        f'<w:tcPr><w:tcBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="{ACCENT}"/>'
        "</w:tcBorders></w:tcPr></w:tblStylePr>"
        "</w:style>"
    )


def set_table_look(tbl: Any, *, first_row: bool, last_row: bool) -> None:
    """Tell Word which of the table style's conditional rows apply to `tbl` (a w:tbl)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    look = tbl.tblPr.find(qn("w:tblLook"))
    if look is None:
        look = OxmlElement("w:tblLook")
        tbl.tblPr.append(look)
    flags = {
        "w:firstRow": first_row,
        "w:lastRow": last_row,
        "w:firstColumn": False,
        "w:lastColumn": False,
        "w:noHBand": True,
        "w:noVBand": True,
    }
    for name, on in flags.items():
        look.set(qn(name), "1" if on else "0")
    value = _LOOK_NO_H_BAND | _LOOK_NO_V_BAND
    value |= _LOOK_FIRST_ROW if first_row else 0
    value |= _LOOK_LAST_ROW if last_row else 0
    look.set(qn("w:val"), f"{value:04X}")


def _add_page_number_footer(document: Any) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    for section in document.sections:
        paragraph = section.footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for kind, text in (
            ("begin", None),
            (None, "PAGE"),
            ("separate", None),
            (None, "1"),
            ("end", None),
        ):
            run = paragraph.add_run()
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor.from_string("7F7F7F")
            if kind is not None:
                field_char = OxmlElement("w:fldChar")
                field_char.set(qn("w:fldCharType"), kind)
                run.element.append(field_char)
            elif text == "PAGE":
                instruction = OxmlElement("w:instrText")
                instruction.set(qn("xml:space"), "preserve")
                instruction.text = " PAGE "
                run.element.append(instruction)
            else:
                run.text = text
