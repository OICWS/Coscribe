"""The line that tells coscribe the user changed a Doc in the app (decision 0025): said once, in
front of the next message, naming the document."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.conversation import docs_edits
from coscribe.conversation.docs_edits import docs_edits_note
from coscribe.tools import (
    WorkspaceScope,
    doc_edits_since_told,
    read_doc_file,
    remember_doc_before_edit,
    save_doc_edits,
)

SOURCE = "---\ncoscribe: doc\ntitle: Plan\n---\n\n# Plan\n\nFirst paragraph.\n\nSecond paragraph.\n"


def _worked_on(monkeypatch: pytest.MonkeyPatch, *paths: str) -> None:
    entries = [{"path": p, "exists": True} for p in paths]
    monkeypatch.setattr(
        docs_edits, "summarize_activity", lambda *_: {"outputs": entries, "references": []}
    )


def test_the_note_names_the_doc_and_goes_in_front_of_the_message_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, scope = tmp_path / "state", WorkspaceScope(tmp_path)
    path = tmp_path / "plan.md"
    path.write_text(SOURCE, encoding="utf-8")
    # A Word file is not a Doc: it is no part of this note.
    (tmp_path / "report.docx").write_bytes(b"x")
    _worked_on(monkeypatch, "plan.md", "report.docx")
    assert docs_edits_note([], {}, scope, state) == ""
    assert doc_edits_since_told(path, state) is None

    remember_doc_before_edit(path, state)
    save_doc_edits(
        path,
        read_doc_file(path)["version"],
        [{"op": "replace", "index": 1, "expected": "First paragraph.", "text": "First, reworded."}],
    )
    note = docs_edits_note([], {}, scope, state)

    assert note.startswith("[The user edited plan.md in the app since your last turn: changed ")
    assert "First, reworded." in note and "report.docx" not in note
    assert note.endswith("]\n\n")
    assert docs_edits_note([], {}, scope, state) == ""
