"""What the user changed in the app since coscribe's last turn, as one note for the next turn: the
slides of a deck, the text of a Doc and the elements of a design's artboards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import BaseMessage

from ..runtime import ToolMetadata
from ..tools import WorkspaceScope
from .activity import summarize_activity
from .board_edits import board_edits_line, board_edits_since_told
from .deck_edits import deck_edits_note
from .design_canvas import canvas_of_page, is_canvas
from .docs_edits import docs_edits_note


def user_edits_note(session: Any, history: list[BaseMessage]) -> str:
    catalog, scope = session.tool_catalog(), session.workspace_scope()
    state_dir = session.settings.state_dir
    return (
        deck_edits_note(history, catalog, scope)
        + docs_edits_note(history, catalog, scope, state_dir)
        + design_edits_note(history, catalog, scope, state_dir)
    )


def design_edits_note(
    messages: list[BaseMessage],
    catalog: dict[str, ToolMetadata],
    scope: WorkspaceScope,
    state_dir: Path,
) -> str:
    """One line for each design this conversation made whose artboards the user edited in the
    properties panel since; telling forgets the edits, so each is said once."""
    activity = summarize_activity(messages, catalog, scope)
    canvases: dict[str, str] = {}
    for entry in [*activity["outputs"], *activity["references"]]:
        try:
            file = scope.resolve(entry["path"])
        except (OSError, ValueError, PermissionError):
            continue
        canvas = file if is_canvas(file) else canvas_of_page(file)
        if canvas is not None:
            canvases.setdefault(str(canvas), scope.relative(canvas))
    lines = [
        board_edits_line(shown, edits)
        for canvas, shown in canvases.items()
        if (edits := board_edits_since_told(Path(canvas), state_dir))
    ]
    return "".join(f"{line}\n" for line in lines) + ("\n" if lines else "")
