"""The deck engine's one tool: build a .pptx from a folder of SVG pages.

Decision 0001 keeps the tool list fixed and small, so the engine adds this tool only: the pages
are written and edited with the file tools the agent already has, and a page is read back with
`read_file`. The page contract lives in this tool's description, which is static.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Optional

from .....runtime import tool_metadata
from ...._file_locks import file_lock
from ...._workspace import WorkspaceScope
from .build import DeckChangedError, build_deck


def build_engine_tools(
    root: str | Path,
    *,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    scope = WorkspaceScope(root, extra_readable=extra_readable, extra_writable=extra_writable)

    # `Optional[list[str]]`, not `list[str] | None`: see `read_pptx` in `tools/presentations.py`
    # for why the tool schema needs `typing.Optional`.
    def build_pptx_from_pages(
        pages_dir: str,
        path: str,
        sources: Optional[list[str]] = None,  # noqa: UP045
        replace_changes: bool = False,
    ) -> dict[str, Any]:
        """Build a PowerPoint deck from a folder of SVG pages, one page per slide, and check it.

        Write the pages with write_file first (`01-cover.svg`, `02-agenda.svg`, ...; slides follow
        the file names) and call this again after any page changes: the pages are the deck's
        source. Every shape and text becomes a native, editable PowerPoint object.

        Page language (anything else is reported as an error):
        - Root: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"
          font-family="Microsoft YaHei, Arial">, the same viewBox on every page; 1 px = 1/96 in.
        - Elements: rect (rx for rounded), circle, ellipse, line, polyline, polygon, path, text
          with tspan, image (href relative to the pages folder, inside the workspace), g. In defs:
          linearGradient, radialGradient, filter with feDropShadow, clipPath for an image, marker.
        - Not allowed: mask, <style>, class, CSS, foreignObject, textPath, animation, script, web
          fonts, HTML entities (write characters; escape & < > as &amp; &lt; &gt;).
        - Colours as #RRGGBB; transparency with fill-opacity, stroke-opacity or opacity.
        - The page's title is one <text id="title">: it becomes the slide title (outline view,
          accessibility, edit_pptx_text).
        - Text never wraps: one <text> per paragraph, each further line a
          <tspan x="(same x)" dy="(line height)">; a styled word is a <tspan> without x/dy.
        - A <g id="..."> per logical unit (card, chart, list item): the id becomes the shape's
          name. A group's transform is translate(x y) only; size and rotate the elements inside.
        - A <rect> covering the whole canvas, drawn first, becomes the slide background.
        - Charts and tables are drawn with shapes and text, every value from the material.

        Returns per page `errors` (fix the page and build again) and `warnings` (judge them: a
        number no source has may be a sum you computed or an axis tick). `sources` are the files
        the content comes from, for that number check.

        Args:
            pages_dir: folder holding the .svg pages, relative to the workspace root
            path: the .pptx to write, relative to the workspace root
            sources: the files the deck's facts come from (documents, sheets, notes)
            replace_changes: only when the user agreed: build even though the .pptx was changed
                after its last build (in PowerPoint or with the edit_pptx_* tools), which throws
                those changes away
        """
        folder = scope.resolve(pages_dir)
        if not folder.is_dir():
            raise ValueError(f"Not a folder: {pages_dir}")
        if not path.lower().endswith(".pptx"):
            raise ValueError(f"path must end in .pptx: {path}")
        out = scope.resolve(path, write=True)
        source_paths = [scope.resolve(s) for s in sources or []]
        for source, given in zip(source_paths, sources or [], strict=True):
            if not source.is_file():
                raise ValueError(f"Source file does not exist: {given}")
        with file_lock(out):
            try:
                report = build_deck(
                    folder,
                    out,
                    sources=source_paths,
                    resource_root=_allowed_root(scope, folder),
                    replace_changes=replace_changes,
                )
            except DeckChangedError as e:
                raise ValueError(
                    f"{e}. Make this change with the edit_pptx_* tools on the .pptx instead, or "
                    "ask the user whether their changes may be replaced (replace_changes)."
                ) from e
        result = report.as_dict()
        result["path"] = scope.relative(out)
        return result

    return [tool_metadata(build_pptx_from_pages, risk_category="WRITE_LOCAL", category="documents")]


def _allowed_root(scope: WorkspaceScope, folder: Path) -> Path:
    """The workspace, or the trusted folder the pages are in: images may come from anywhere in
    it, and from nowhere outside it."""
    for root in (scope.root, *scope.extra_readable):
        if folder == root or root in folder.parents:
            return root
    return folder
