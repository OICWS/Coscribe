"""The deck engine: a deck's page sources (SVG) compiled into native PowerPoint shapes.

Part 1 (issue #141): the compiler only; no tool calls it yet.
"""

from .compiler import TITLE_ID, CompileReport, PageReport, compile_pages

__all__ = ["TITLE_ID", "CompileReport", "PageReport", "compile_pages"]
