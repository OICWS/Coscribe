"""PowerPoint: the deck engine (compiled page sources) and, until `tools/presentations.py` is split
along the engine / edit / motion / qa / xml / templates boundary, the tools that still live there.
`build_presentation_tools` here is the one the coordinator registers: today's tools and the
engine's together."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .engine.build import DeckChangedError
from .engine.design_system import design_system
from .engine.instructions import NEW_DECK_INSTRUCTIONS
from .engine.section_format import SectionError
from .engine.tool import build_engine_tools
from .engine.view import NotBuiltFromPages, read_deck, slide_svg
from .engine.view_arrange import delete_slide, duplicate_slide, insert_slide, move_slide
from .engine.view_changes import deck_edits_since_coscribe
from .engine.view_comments import (
    CommentNotFound,
    add_comment,
    delete_comment,
    read_comments,
    reply_to_comment,
    resolve_comment,
)
from .engine.view_edit import SlideChanged, add_slide_asset, save_slide, slide_parts
from .engine.view_export import deck_basic_fonts, deck_html, deck_pdf
from .engine.view_foreign import foreign_deck, foreign_slide_svg
from .engine.view_history import deck_history, step_history
from .tool_wrappers import build_presentation_tools as build_legacy_presentation_tools
from .toolkit import PresentationToolkit

__all__ = [
    "CommentNotFound",
    "DeckChangedError",
    "NEW_DECK_INSTRUCTIONS",
    "NotBuiltFromPages",
    "PresentationToolkit",
    "SectionError",
    "SlideChanged",
    "add_comment",
    "add_slide_asset",
    "build_legacy_presentation_tools",
    "build_presentation_tools",
    "deck_basic_fonts",
    "deck_edits_since_coscribe",
    "deck_history",
    "deck_html",
    "deck_pdf",
    "design_system",
    "delete_comment",
    "delete_slide",
    "duplicate_slide",
    "foreign_deck",
    "foreign_slide_svg",
    "insert_slide",
    "move_slide",
    "read_comments",
    "read_deck",
    "reply_to_comment",
    "resolve_comment",
    "save_slide",
    "slide_parts",
    "slide_svg",
    "step_history",
]


def build_presentation_tools(
    root: str | Path,
    *,
    state_dir: str | Path | None = None,
    custom_templates_dir: str | Path | None = None,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    return [
        *build_legacy_presentation_tools(
            root,
            state_dir=state_dir,
            custom_templates_dir=custom_templates_dir,
            extra_readable=extra_readable,
            extra_writable=extra_writable,
        ),
        *build_engine_tools(root, extra_readable=extra_readable, extra_writable=extra_writable),
    ]
