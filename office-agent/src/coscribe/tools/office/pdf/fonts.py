"""A reportlab font with Chinese glyphs, for write_pdf."""

from __future__ import annotations

from pathlib import Path

# Where a font with Chinese glyphs usually lives, best looking first. A
# TrueType file or collection: reportlab can't use PostScript-outline
# (CFF) fonts such as Noto Sans CJK, which are skipped when they fail.
_CJK_FONT_FILES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyh.ttf",
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
)
_pdf_cjk_font_name: str | None = None


def _pdf_cjk_font() -> str | None:
    """A registered reportlab font with Chinese glyphs: a system TrueType
    font, embedded, or failing that the built-in STSong-Light CID font
    (not embedded; the viewer supplies the glyphs). Cached."""
    global _pdf_cjk_font_name
    if _pdf_cjk_font_name is not None:
        return _pdf_cjk_font_name
    from reportlab.lib.fonts import addMapping
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    name = "CoscribeCJK"
    for candidate in _CJK_FONT_FILES:
        if not Path(candidate).is_file():
            continue
        try:
            font = TTFont(name, candidate, subfontIndex=0)
        except Exception:  # noqa: BLE001 -- an unusable file: try the next
            continue
        if ord("国") not in font.face.charToGlyph:
            continue
        pdfmetrics.registerFont(font)
        break
    else:
        name = "STSong-Light"
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(name))
        except Exception:  # noqa: BLE001 -- no CJK support at all: leave the default
            return None
    # <b>/<i> inside a paragraph look the font up as a family.
    pdfmetrics.registerFontFamily(name, normal=name, bold=name, italic=name, boldItalic=name)
    for bold in (0, 1):
        for italic in (0, 1):
            addMapping(name, bold, italic, name)
    _pdf_cjk_font_name = name
    return name
