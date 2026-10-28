"""What the user changed in the app since coscribe's last turn, as one note for the next turn: the
slides of a deck and the text of a Doc."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage

from .deck_edits import deck_edits_note
from .docs_edits import docs_edits_note


def user_edits_note(session: Any, history: list[BaseMessage]) -> str:
    catalog, scope = session.tool_catalog(), session.workspace_scope()
    return deck_edits_note(history, catalog, scope) + docs_edits_note(
        history, catalog, scope, session.settings.state_dir
    )
