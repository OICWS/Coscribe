"""The deck engine: a deck's page sources (SVG) compiled into native PowerPoint shapes, checked,
and rebuilt only while the .pptx is still what they built (decision 0010).

`tool.py` is its one tool, `build_pptx_from_pages`; `guide/` holds the skill and the paragraph of
instructions that would offer it for new decks. The product does not load them yet: the
evaluation's `engine` route does, and decides whether the engine replaces today's route.
"""

from .build import MANIFEST, BuildReport, DeckChangedError, build_deck, page_files, slide_hashes
from .checker import check_deck, source_text
from .compiler import TITLE_ID, CompileReport, PageReport, compile_pages

__all__ = [
    "MANIFEST",
    "TITLE_ID",
    "BuildReport",
    "CompileReport",
    "DeckChangedError",
    "PageReport",
    "build_deck",
    "check_deck",
    "compile_pages",
    "page_files",
    "slide_hashes",
    "source_text",
]
