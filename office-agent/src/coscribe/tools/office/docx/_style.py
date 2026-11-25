"""The house style a new document gets when it is not built on the user's template."""

from __future__ import annotations

import re
from typing import Any

ACCENT = "1F4E79"
_HEADING_GREY = "262626"
_BORDER_GREY = "BFBFBF"
LATIN_FONT = "Calibri"
EAST_ASIAN_FONT = "Microsoft YaHei"
# The East Asian face, and the theme's script code, for each language a document can be marked.
# The faces are written by their own local names: Word (16, Windows) ignored "Microsoft YaHei" in
# the document defaults and fell back to SimSun, while it resolves the local name everywhere.
_EAST_ASIAN = {
    "zh-CN": ("微软雅黑", "Hans"),
    "zh-TW": ("微軟正黑體", "Hant"),
    "ja-JP": ("游ゴシック", "Jpan"),
    "ko-KR": ("맑은 고딕", "Hang"),
}
_LANGUAGE_ALIASES = {
    "zh": "zh-CN",
    "zh-hans": "zh-CN",
    "zh-sg": "zh-CN",
    "zh-hant": "zh-TW",
    "zh-hk": "zh-TW",
    "zh-mo": "zh-TW",
    "ja": "ja-JP",
    "ko": "ko-KR",
}
_LANGUAGE_TAG = re.compile(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*")
_KANA = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
_HANGUL = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
TABLE_STYLE_ID = "ReportTable"
_TABLE_STYLE_NAME = "Report Table"

_CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")
_TOTAL_LABEL = re.compile(
    r"^\s*(\*\*)?\s*(grand total|totals?|sum|合计|总计|小计|总额|共计)\b", re.IGNORECASE
)

# (level, size in pt, space before in pt, colour)
_HEADINGS = ((1, 16.0, 12.0, ACCENT), (2, 13.0, 10.0, ACCENT), (3, 11.5, 8.0, _HEADING_GREY))

A4_EMU = (7560310, 10692130)

# tblLook's legacy w:val bits, still read by Word before 2010.
_LOOK_FIRST_ROW = 0x0020
_LOOK_LAST_ROW = 0x0040
_LOOK_NO_H_BAND = 0x0200
_LOOK_NO_V_BAND = 0x0400


TITLE_STYLE = "Title"


def has_cjk(text: str) -> bool:
    return bool(_CJK.search(text))


def document_language(language: str, text: str) -> str:
    """The language a new document is marked in: `language` as the model gave it (a tag such as
    "zh-CN", "ja", "en-GB"), else the script of `text`, else US English."""
    language = language.strip()
    if language:
        if not _LANGUAGE_TAG.fullmatch(language):
            raise ValueError(
                f'language is a language tag such as "zh-CN" or "en-US", got {language!r}'
            )
        canonical = _LANGUAGE_ALIASES.get(language.lower())
        if canonical:
            return canonical
        main, _, region = language.partition("-")
        return f"{main.lower()}-{region.upper()}" if region else main.lower()
    if _KANA.search(text):
        return "ja-JP"
    if _HANGUL.search(text):
        return "ko-KR"
    return "zh-CN" if has_cjk(text) else "en-US"


def is_total_row(row: list[str]) -> bool:
    return bool(row) and bool(_TOTAL_LABEL.match(row[0]))


def apply_house_style(document: Any, *, language: str) -> None:
    """Restyle a blank python-docx document: fonts, spacing, headings, a
    table style, A4 paper and a page-number footer. Spacing and fonts go into the
    document defaults rather than Normal, because a table style overrides
    the defaults but not a paragraph style: set on Normal, the body spacing
    would leak into every table cell."""
    from docx.oxml.ns import qn

    styles_element = document.styles.element
    defaults = styles_element.find(qn("w:docDefaults"))
    run_defaults = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    east_asian = _EAST_ASIAN.get(language)
    face = east_asian[0] if east_asian else _EAST_ASIAN["zh-CN"][0]
    _set_fonts(run_defaults, face)
    _set_language(document, run_defaults, language)
    size = "21" if east_asian else "22"
    for tag in ("w:sz", "w:szCs"):
        run_defaults.find(qn(tag)).set(qn("w:val"), size)
    spacing = defaults.find(qn("w:pPrDefault")).find(qn("w:pPr")).find(qn("w:spacing"))
    # 4 pt after and 1.1 lines: a one-page memo with a small table still fits one A4 page.
    spacing.set(qn("w:after"), "80")
    spacing.set(qn("w:line"), "264")
    spacing.set(qn("w:lineRule"), "auto")

    for level, size_pt, before_pt, colour in _HEADINGS:
        _style_heading(document.styles[f"Heading {level}"], size_pt, before_pt, colour, face)
    _style_heading(document.styles["Title"], 22.0, 0.0, ACCENT, face)
    styles_element.append(_table_style_element())
    for section in document.sections:
        # python-docx's blank document is US Letter; A4 is the paper nearly everywhere else.
        section.page_width, section.page_height = A4_EMU
    _add_page_number_footer(document)


def _set_fonts(r_pr: Any, east_asian_face: str) -> None:
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
    fonts.set(qn("w:eastAsia"), east_asian_face)


def _set_language(document: Any, run_defaults: Any, language: str) -> None:
    """Mark the document's language. With an English East Asian language Word draws the shared
    punctuation (curly quotes, dashes, ellipses) of Chinese, Japanese or Korean text in the Latin
    face, narrow and breakable from its character; python-docx's template also carries a Japanese
    theme language, which sends every theme-font style (Heading 4 and below, captions, tables) to
    MS Mincho and MS Gothic."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    lang = run_defaults.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        run_defaults.append(lang)
    theme_lang = document.settings.element.find(qn("w:themeFontLang"))
    east_asian = _EAST_ASIAN.get(language)
    if east_asian is None:
        lang.set(qn("w:val"), language)
        if theme_lang is not None:
            theme_lang.set(qn("w:val"), language)
        return
    run_defaults.find(qn("w:rFonts")).set(qn("w:hint"), "eastAsia")
    lang.set(qn("w:eastAsia"), language)
    if theme_lang is not None:
        theme_lang.set(qn("w:eastAsia"), language)
    _set_theme_east_asian_font(document, *east_asian)


def _set_theme_east_asian_font(document: Any, face: str, script_code: str) -> None:
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from lxml import etree

    try:
        theme = document.part.part_related_by(RT.THEME)
    except KeyError:
        return
    drawing = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    root = etree.fromstring(theme.blob)
    for role in ("majorFont", "minorFont"):
        for font in root.iter(f"{drawing}{role}"):
            ea = font.find(f"{drawing}ea")
            if ea is not None:
                ea.set("typeface", face)
            for script in font.iter(f"{drawing}font"):
                if script.get("script") == script_code:
                    script.set("typeface", face)
    # A plain Part has no blob setter; its bytes live in this attribute.
    vars(theme)["_blob"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def _style_heading(
    style: Any, size_pt: float, before_pt: float, colour: str, east_asian_face: str
) -> None:
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    _set_fonts(style.element.get_or_add_rPr(), east_asian_face)
    style.font.size = Pt(size_pt)
    style.font.bold = True
    style.font.color.rgb = RGBColor.from_string(colour)
    p_pr = style.element.get_or_add_pPr()
    spacing = p_pr.find(qn("w:spacing"))
    if spacing is None:
        from docx.oxml import OxmlElement

        spacing = OxmlElement("w:spacing")
        p_pr.append(spacing)
    spacing.set(qn("w:before"), str(round(before_pt * 20)))
    spacing.set(qn("w:after"), "80")


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
        '</w:tblBorders><w:tblCellMar><w:top w:w="20" w:type="dxa"/>'
        '<w:left w:w="100" w:type="dxa"/><w:bottom w:w="20" w:type="dxa"/>'
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
