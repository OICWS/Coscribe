"""The deck engine: a deck's page sources (SVG) compiled into native PowerPoint shapes, checked,
and rebuilt only while the .pptx is still what they built (decision 0010).

`tool.py` is its one tool, `build_pptx_from_pages`. New decks are built with it: the coordinator's
instructions say so, and the built-in skill "PPTX Pages" (`builtin_skills/pptx-pages/`) is the
guide the agent loads first.

`sections.py` compiles the other source language, positioned HTML sections (decision 0015): a
slide becomes one when it is first edited (decision 0016), converted with its content unchanged
by `svg_to_section.py` (`convert_slide`), and a deck's folder may hold both kinds. Nothing
converts a slide yet.
"""

from .build import (
    MANIFEST,
    BuildReport,
    DeckChangedError,
    build_deck,
    built_from_pages,
    convert_slide,
    page_files,
    slide_hashes,
)
from .checker import check_deck, source_text
from .compiler import TITLE_ID, CompileReport, PageReport, compile_pages
from .sections import check_sections, compile_sections
from .svg_to_section import convert_page

__all__ = [
    "MANIFEST",
    "TITLE_ID",
    "BuildReport",
    "CompileReport",
    "DeckChangedError",
    "PageReport",
    "build_deck",
    "built_from_pages",
    "check_deck",
    "check_sections",
    "compile_pages",
    "compile_sections",
    "convert_page",
    "convert_slide",
    "page_files",
    "slide_hashes",
    "source_text",
]
