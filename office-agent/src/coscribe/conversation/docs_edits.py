"""The line that tells coscribe the user changed a Word document in the app since its last turn
(decision 0019, as `deck_edits.py` does for decks). It goes in front of the user's message with the
turn's other notes, never into the system prompt or the tool list."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import BaseMessage

from ..runtime import ToolMetadata
from ..tools import WorkspaceScope, edits_since_told
from .activity import summarize_activity


def docs_edits_note(
    messages: list[BaseMessage],
    catalog: dict[str, ToolMetadata],
    scope: WorkspaceScope,
    state_dir: Path,
) -> str:
    """One line for each document this conversation has worked on that the user changed since, or
    an empty string. Reporting a change forgets it, so it is said once."""
    activity = summarize_activity(messages, catalog, scope)
    lines = []
    for entry in [*activity["outputs"], *activity["references"]]:
        if not entry["exists"] or not entry["path"].lower().endswith(".docx"):
            continue
        try:
            found = edits_since_told(scope.resolve(entry["path"]), state_dir)
        except (OSError, ValueError, KeyError):
            continue
        if found is not None:
            lines.append(_line(entry["path"], found))
    return "".join(f"{line}\n" for line in lines) + ("\n" if lines else "")


def _line(path: str, found: dict[str, list[str]]) -> str:
    parts = [
        f"{what} {'; '.join(items)}"
        for what, items in (
            ("changed", found["changed"]),
            ("added", found["added"]),
            ("removed", found["removed"]),
        )
        if items
    ]
    return (
        f"[The user edited {path} in the app since your last turn: {'; '.join(parts)}. "
        "Read the document before you change it, and do not write it again from an older copy.]"
    )
