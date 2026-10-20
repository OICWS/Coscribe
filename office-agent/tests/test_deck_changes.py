"""Telling coscribe what the user changed in a deck since it last knew it (issue #462): the net
difference between coscribe's last build (or the last time it was told) and the pages now."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.tools.office.pptx import (
    deck_edits_since_coscribe,
    save_slide,
    slide_parts,
    step_history,
)
from coscribe.tools.office.pptx.engine import build_deck

from .test_deck_engine import CARDS, COVER


def _deck(tmp_path: Path) -> Path:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01-cover.svg").write_text(COVER, encoding="utf-8")
    (folder / "02-cards.svg").write_text(CARDS, encoding="utf-8")
    assert build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path).ok
    return tmp_path / "deck.pptx"


def _edit(deck: Path, tmp_path: Path, index: int = 0) -> None:
    read = slide_parts(deck, index, tmp_path)
    source = read["source"].replace("<section", '<section data-transition="fade"', 1)
    save_slide(deck, index, source=source, version=read["version"], resource_root=tmp_path)


def test_nothing_to_tell_while_coscribe_built_the_last_state(tmp_path: Path) -> None:
    assert deck_edits_since_coscribe(_deck(tmp_path)) is None


def test_an_edit_is_reported_once_with_the_page_it_changed(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    _edit(deck, tmp_path)
    found = deck_edits_since_coscribe(deck)
    # The first edit turns the page into a section, so its file is a new one.
    assert found == {
        "folder": "pages",
        "edited": [],
        "added": ["01-cover.html"],
        "removed": ["01-cover.svg"],
    }
    assert deck_edits_since_coscribe(deck) is None  # said once


def test_a_later_edit_is_reported_again_as_an_edit(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    _edit(deck, tmp_path)
    deck_edits_since_coscribe(deck)
    read = slide_parts(deck, 0, tmp_path)
    save_slide(
        deck,
        0,
        source=read["source"].replace('data-transition="fade"', 'data-transition="push"'),
        version=read["version"],
        resource_root=tmp_path,
    )
    found = deck_edits_since_coscribe(deck)
    assert found is not None and found["edited"] == ["01-cover.html"]


def test_an_edit_that_was_undone_is_not_reported(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    _edit(deck, tmp_path)
    step_history(deck, -1, resource_root=tmp_path)
    assert deck_edits_since_coscribe(deck) is None


def test_coscribes_own_build_after_an_edit_leaves_nothing_to_tell(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    _edit(deck, tmp_path)
    folder = tmp_path / "pages"
    (folder / "02-cards.svg").write_text(CARDS.replace("</svg>", "<rect/></svg>"), encoding="utf-8")
    build_deck(folder, deck, resource_root=tmp_path, replace_changes=True)
    assert deck_edits_since_coscribe(deck) is None


def test_a_deck_not_built_from_pages_has_nothing_to_tell(tmp_path: Path) -> None:
    other = tmp_path / "other.pptx"
    other.write_bytes(b"")
    assert deck_edits_since_coscribe(other) is None


@pytest.mark.parametrize("by", ["you"])
def test_a_deck_with_no_build_of_coscribes_has_nothing_to_compare_with(
    tmp_path: Path, by: str
) -> None:
    deck = _deck(tmp_path)
    log = tmp_path / "pages" / ".history" / "states.json"
    log.write_text(log.read_text(encoding="utf-8").replace('"coscribe"', f'"{by}"'), "utf-8")
    assert deck_edits_since_coscribe(deck) is None
