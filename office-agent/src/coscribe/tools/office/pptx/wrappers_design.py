"""The tool that reads a deck's design as facts, for making a design system from a template."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .toolkit import PresentationToolkit


def build_design_tools(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def read_pptx_design(path: str) -> dict[str, object]:
        """Read what a .pptx (a company template, say) says about its look,
        as facts: the master theme's 12 colors (`dk1`..`folHlink`, 6 hex
        digits, no `#`), its heading and body fonts, the master's title and
        body text sizes (in points and as pixels on a 1920 px wide slide, the
        size a Coscribe design system uses), the slide size, and the names of
        its layouts. Use it to build a design system from a template: read
        this, look at a few slides with `render_pptx_preview`, then save the
        system with `save_design_system`. It reads the master only; colors or
        fonts a slide sets by hand are not listed.

        Args:
            path: file to read, relative to the workspace root
        """
        return toolkit.read_pptx_design(path=path)

    return {"read_pptx_design": read_pptx_design}
