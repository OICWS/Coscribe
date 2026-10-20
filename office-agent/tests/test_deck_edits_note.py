"""The line that tells coscribe the user changed slides in the app (issue #462)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from coscribe.conversation import deck_edits
from coscribe.conversation.deck_edits import deck_edits_note
from coscribe.tools import WorkspaceScope
from coscribe.tools.office.pptx import save_slide, slide_parts
from coscribe.tools.office.pptx.engine import build_deck

from .test_deck_engine import CARDS, COVER


@pytest.fixture
def deck(tmp_path: Path) -> Path:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01-cover.svg").write_text(COVER, encoding="utf-8")
    (folder / "02-cards.svg").write_text(CARDS, encoding="utf-8")
    assert build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path).ok
    return tmp_path / "deck.pptx"


def _worked_on(monkeypatch: pytest.MonkeyPatch, *paths: str) -> None:
    entries = [{"path": p, "exists": True} for p in paths]
    monkeypatch.setattr(
        deck_edits,
        "summarize_activity",
        lambda *_: {"outputs": entries, "references": []},
    )


def _scope(tmp_path: Path) -> WorkspaceScope:
    return WorkspaceScope(tmp_path)


def _edit(deck: Path, tmp_path: Path) -> None:
    read = slide_parts(deck, 1, tmp_path)
    source = read["source"].replace("<section", '<section data-transition="fade"', 1)
    save_slide(deck, 1, source=source, version=read["version"], resource_root=tmp_path)


def test_the_note_names_the_deck_and_the_pages_the_user_changed_once(
    deck: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _worked_on(monkeypatch, "deck.pptx")
    catalog: dict[str, Any] = {}
    assert deck_edits_note([], catalog, _scope(tmp_path)) == ""
    _edit(deck, tmp_path)
    note = deck_edits_note([], catalog, _scope(tmp_path))
    assert note.startswith("[The user changed the slides of deck.pptx in the app")
    assert "added 02-cards.html" in note and "removed 02-cards.svg" in note
    assert "pages in pages/" in note and note.endswith("]\n\n")
    assert deck_edits_note([], catalog, _scope(tmp_path)) == ""  # said once


def test_other_files_and_missing_decks_are_left_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "notes.docx").write_bytes(b"")
    _worked_on(monkeypatch, "notes.docx", "gone.pptx")
    assert deck_edits_note([], {}, _scope(tmp_path)) == ""
