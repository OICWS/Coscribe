"""The line that tells coscribe the user changed slides in the app since its last turn (issue
#462). It goes in front of the user's message with the turn's other notes, never into the system
prompt or the tool list, so what the provider has cached is untouched."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from langchain_core.messages import BaseMessage

from ..runtime import ToolMetadata
from ..tools import NotBuiltFromPages, WorkspaceScope, deck_edits_since_coscribe
from .activity import summarize_activity

_MAX_NAMES = 12


def deck_edits_note(
    messages: list[BaseMessage], catalog: dict[str, ToolMetadata], scope: WorkspaceScope
) -> str:
    """One line for each deck this conversation has worked on that the user changed since, or an
    empty string. Reporting a change marks it told, so it is said once."""
    activity = summarize_activity(messages, catalog, scope)
    lines = []
    for entry in [*activity["outputs"], *activity["references"]]:
        if not entry["exists"] or not entry["path"].lower().endswith(".pptx"):
            continue
        try:
            found = deck_edits_since_coscribe(scope.resolve(entry["path"]))
        except (NotBuiltFromPages, OSError, ValueError):
            continue
        if found is not None:
            lines.append(_line(entry["path"], found))
    return "".join(f"{line}\n" for line in lines) + ("\n" if lines else "")


def _line(deck: str, found: dict[str, Any]) -> str:
    parts = [
        f"{what} {_names(names)}"
        for what, names in (
            ("edited", found["edited"]),
            ("added", found["added"]),
            ("removed", found["removed"]),
        )
        if names
    ]
    return (
        f"[The user changed the slides of {deck} in the app since your last turn: "
        f"{'; '.join(parts)} (pages in {_folder(deck, found['folder'])}/). Read those pages "
        "before you change these slides, and do not rebuild them from older sources.]"
    )


def _names(names: list[str]) -> str:
    shown = ", ".join(names[:_MAX_NAMES])
    return shown + (f" and {len(names) - _MAX_NAMES} more" if len(names) > _MAX_NAMES else "")


def _folder(deck: str, name: str) -> str:
    return str(PurePosixPath(deck.replace("\\", "/")).with_name(name))
