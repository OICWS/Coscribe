"""PowerPoint: the deck engine (compiled page sources) and, until `tools/presentations.py` is split
along the engine / edit / motion / qa / xml / templates boundary, the tools that still live there.
`build_presentation_tools` here is the one the coordinator registers: today's tools and the
engine's together."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .engine.instructions import NEW_DECK_INSTRUCTIONS
from .engine.tool import build_engine_tools
from .engine.view import NotBuiltFromPages, read_deck, slide_svg
from .engine.view_export import deck_basic_fonts, deck_html, deck_pdf
from .tool_wrappers import build_presentation_tools as build_legacy_presentation_tools
from .toolkit import PresentationToolkit

__all__ = [
    "NEW_DECK_INSTRUCTIONS",
    "NotBuiltFromPages",
    "PresentationToolkit",
    "build_legacy_presentation_tools",
    "build_presentation_tools",
    "deck_basic_fonts",
    "deck_html",
    "deck_pdf",
    "read_deck",
    "slide_svg",
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
