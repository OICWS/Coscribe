"""The before and after picture on the approval card of a document edit."""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ..tools import DocumentToolkit, SpreadsheetToolkit, WorkspaceScope
from ..tools._thumbnail import render_single_page_preview
from ..tools.presentations import PresentationToolkit

logger = logging.getLogger(__name__)

# build_document_edit_preview's dispatch table: which toolkit class
# owns an approval-gated edit tool, keyed by the target file's extension
# -- all three toolkits share the same (root, *, state_dir=,
# extra_readable=, extra_writable=) constructor shape (see that method's
# own docstring), which is what makes a single dict lookup enough instead
# of three near-duplicate preview-building methods.
PREVIEWABLE_TOOLKITS_BY_EXTENSION: dict[str, type[Any]] = {
    ".pptx": PresentationToolkit,
    ".potx": PresentationToolkit,
    ".docx": DocumentToolkit,
    ".dotx": DocumentToolkit,
    ".xlsx": SpreadsheetToolkit,
    ".xlsm": SpreadsheetToolkit,
    ".xltx": SpreadsheetToolkit,
}


async def build_document_edit_preview(
    tool_name_: str,
    args: dict[str, Any],
    workspace_root: str | Path,
    extra_readable: Sequence[str | Path],
    extra_writable: Sequence[str | Path],
    state_dir: Path,
) -> tuple[str | None, str | None]:
    """Best-effort before/after preview for an approval-gated
    document edit (pptx/docx/xlsx) -- dry-runs the *exact* same tool
    call, with the *exact* same args, against a throwaway copy of the
    target file, so the approval card can show what the edit will
    actually produce instead of the raw JSON arguments dump it fell
    back to before (`{"shape_index": 3, "fill_color": "38BDF8"}`
    tells a user little about what's about to change; a picture
    does). Reusing the real edit method this way -- not a second,
    hand-written "what would this look like" implementation -- means
    the preview can never drift out of sync with what actually
    happens on approval.

    Deliberately generic, not a hardcoded per-tool dispatch table:
    `PREVIEWABLE_TOOLKITS_BY_EXTENSION` below maps a file extension
    to its toolkit class (PresentationToolkit/DocumentToolkit/
    SpreadsheetToolkit -- all three share the same `(root, *,
    state_dir=, extra_readable=, extra_writable=)` constructor
    shape, which is what makes this dispatch table-driven instead of
    three near-duplicate copies of this method); applies to *any*
    tool name that happens to be a method on that class (private
    helpers are all `_`-prefixed, so this can't accidentally match
    one) whose `path` argument names an existing file with a
    recognized extension -- covers every current and future edit
    tool across all three formats with zero maintenance here, and
    naturally excludes a pure-create tool like `fill_pptx_template`
    (no existing file to diff against) without needing a denylist --
    `write_pptx`/`write_docx`/`write_xlsx` *do* get previewed when
    they're actually overwriting something that already exists,
    which is exactly the case worth previewing.

    Never raises and never touches the real file -- any failure
    (soffice missing, a bad dry-run, a locked file, an
    unrecognized extension) just means one or both preview images
    come back None, and the approval flow proceeds exactly as it did
    before this existed.
    """
    path_arg = args.get("path")
    if not isinstance(path_arg, str):
        return None, None
    toolkit_cls = PREVIEWABLE_TOOLKITS_BY_EXTENSION.get(Path(path_arg.lower()).suffix)
    if toolkit_cls is None:
        return None, None
    if tool_name_.startswith("_") or not hasattr(toolkit_cls, tool_name_):
        return None, None
    try:
        real_scope = WorkspaceScope(
            workspace_root, extra_readable=extra_readable, extra_writable=extra_writable
        )
        real_path = real_scope.resolve(path_arg)
    except (PermissionError, OSError):
        return None, None
    if not real_path.is_file():
        return None, None

    # "slide" is pptx's own page-selector arg name -- docx/xlsx tool
    # calls never carry one, so they fall through to page 1, the
    # same default an argument-less pptx edit (e.g.
    # edit_pptx_theme_colors, which is deck-wide) already gets.
    slide = args.get("slide")
    page = slide if isinstance(slide, int) and slide > 0 else 1

    before_name, _ = await asyncio.to_thread(
        render_single_page_preview, real_path, state_dir, page
    )

    after_name: str | None = None
    tmp_dir = tempfile.mkdtemp(prefix="coscribe_preview_edit_")
    try:
        preview_path = Path(tmp_dir) / real_path.name
        shutil.copyfile(real_path, preview_path)
        preview_toolkit = toolkit_cls(tmp_dir)
        method = getattr(preview_toolkit, tool_name_)
        dry_run_args = {**args, "path": preview_path.name}
        try:
            await asyncio.to_thread(lambda: method(**dry_run_args))
        except Exception:
            logger.debug(
                "approval preview: dry run of %s failed, showing 'before' only",
                tool_name_,
                exc_info=True,
            )
            return before_name, None
        after_name, _ = await asyncio.to_thread(
            render_single_page_preview, preview_path, state_dir, page
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return before_name, after_name
