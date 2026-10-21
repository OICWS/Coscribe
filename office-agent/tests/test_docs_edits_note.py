"""The line that tells coscribe the user changed a Word document in the app (decision 0019): the
net difference since the editor's first save, said once, with an undone edit not reported."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from coscribe.conversation import docs_edits
from coscribe.conversation.docs_edits import docs_edits_note
from coscribe.tools import (
    WorkspaceScope,
    edits_since_told,
    read_doc_blocks,
    remember_before_edit,
    save_doc_blocks,
)
from coscribe.tools.office.document_tools import build_document_tools

CONTENT = "# Plan\n\n## Scope\n\nFirst paragraph.\n\nSecond paragraph.\n\n- one\n- two\n"


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    tools = {t.__name__: t for t in build_document_tools(tmp_path)}  # type: ignore[attr-defined]
    tools["write_docx"](path="plan.docx", content=CONTENT)
    return tmp_path / "plan.docx"


def _edit(path: Path, state: Path, change: Any) -> None:
    """What the editor's route does: remember, then save the blocks as changed."""
    remember_before_edit(path, state)
    read = read_doc_blocks(path)
    blocks = change(read["blocks"])
    save_doc_blocks(path, read["version"], blocks)


def _text(block: dict[str, Any]) -> str:
    return "".join(r["t"] for r in block.get("runs", []))


def _at(blocks: list[dict[str, Any]], words: str) -> dict[str, Any]:
    return next(b for b in blocks if words in _text(b))


def _reword(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _at(blocks, "First paragraph")["runs"] = [{"t": "First paragraph, reworded."}]
    blocks.remove(_at(blocks, "Second paragraph"))
    blocks.append({"kind": "heading", "level": 2, "runs": [{"t": "Appendix"}]})
    return blocks


def test_what_the_person_changed_added_and_removed_is_told_once(doc: Path, tmp_path: Path) -> None:
    state = tmp_path / "state"
    assert edits_since_told(doc, state) is None  # nothing remembered yet
    _edit(doc, state, _reword)
    found = edits_since_told(doc, state)
    assert found == {
        "changed": ["paragraph: First paragraph. -> paragraph: First paragraph, reworded."],
        "added": ["heading: Appendix"],
        "removed": ["paragraph: Second paragraph."],
    }
    assert edits_since_told(doc, state) is None  # said once


def test_an_edit_that_was_undone_is_not_reported(doc: Path, tmp_path: Path) -> None:
    state = tmp_path / "state"

    def reword(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        _at(blocks, "First paragraph")["runs"] = [{"t": "Something else."}]
        return blocks

    def restore(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        _at(blocks, "Something else")["runs"] = [{"t": "First paragraph."}]
        return blocks

    _edit(doc, state, reword)
    _edit(doc, state, restore)  # the first remembered state is kept, not replaced
    assert edits_since_told(doc, state) is None


def test_later_edits_start_from_what_coscribe_was_told(doc: Path, tmp_path: Path) -> None:
    state = tmp_path / "state"
    _edit(doc, state, _reword)
    edits_since_told(doc, state)

    def again(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        _at(blocks, "Scope")["runs"] = [{"t": "Scope and goals"}]
        return blocks

    _edit(doc, state, again)
    found = edits_since_told(doc, state)
    assert found is not None and list(found["changed"]) == [
        "heading: Scope -> heading: Scope and goals"
    ]
    assert found["added"] == [] and found["removed"] == []


def test_a_long_list_of_changes_is_cut(doc: Path, tmp_path: Path) -> None:
    state = tmp_path / "state"

    def many(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return blocks + [{"kind": "paragraph", "runs": [{"t": f"extra {i}"}]} for i in range(20)]

    _edit(doc, state, many)
    found = edits_since_told(doc, state)
    assert found is not None and len(found["added"]) == 13 and found["added"][-1] == "and 8 more"


def _worked_on(monkeypatch: pytest.MonkeyPatch, *paths: str) -> None:
    entries = [{"path": p, "exists": True} for p in paths]
    monkeypatch.setattr(
        docs_edits, "summarize_activity", lambda *_: {"outputs": entries, "references": []}
    )


def test_the_note_names_the_document_and_goes_in_front_of_the_message_once(
    doc: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, scope = tmp_path / "state", WorkspaceScope(tmp_path)
    _worked_on(monkeypatch, "plan.docx", "notes.md")
    assert docs_edits_note([], {}, scope, state) == ""
    _edit(doc, state, _reword)
    note = docs_edits_note([], {}, scope, state)
    assert note.startswith("[The user edited plan.docx in the app since your last turn: changed ")
    assert "added heading: Appendix" in note and "removed paragraph: Second paragraph." in note
    assert note.endswith("]\n\n")
    assert docs_edits_note([], {}, scope, state) == ""
