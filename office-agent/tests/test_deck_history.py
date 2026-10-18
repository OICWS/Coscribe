"""Undo and redo in the Slides panel (design §9): every build records the pages, an undo puts
the previous ones back and builds the deck, a change after an undo drops what was undone."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.tools.office.pptx import (
    deck_history,
    read_deck,
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


def _save(deck: Path, tmp_path: Path, transition: str) -> None:
    read = slide_parts(deck, 0, tmp_path)
    source = read["source"].replace("<section", f'<section data-transition="{transition}"', 1)
    save_slide(deck, 0, source=source, version=read["version"], resource_root=tmp_path)


def test_an_edit_is_undone_and_redone(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    assert deck_history(deck) == {"undo": None, "redo": None}
    _save(deck, tmp_path, "fade")
    assert deck_history(deck) == {"undo": "you", "redo": None}

    assert step_history(deck, -1, resource_root=tmp_path) == {"undo": None, "redo": "you"}
    names = [s["name"] for s in read_deck(deck)["slides"]]
    assert names == ["01-cover.svg", "02-cards.svg"] and not read_deck(deck)["changed"]
    assert not (tmp_path / "pages" / "01-cover.html").exists()

    step_history(deck, 1, resource_root=tmp_path)
    assert read_deck(deck)["slides"][0]["transition"] == "fade"
    with pytest.raises(ValueError):
        step_history(deck, 1, resource_root=tmp_path)


def test_coscribes_build_is_one_step_and_a_new_change_drops_the_undone_ones(
    tmp_path: Path,
) -> None:
    deck = _deck(tmp_path)
    folder = tmp_path / "pages"
    (folder / "02-cards.svg").write_text(CARDS.replace("</svg>", "<rect/></svg>"), "utf-8")
    build_deck(folder, deck, resource_root=tmp_path)
    assert deck_history(deck)["undo"] == "coscribe"
    step_history(deck, -1, resource_root=tmp_path)
    assert (folder / "02-cards.svg").read_text(encoding="utf-8") == CARDS
    _save(deck, tmp_path, "push")
    assert deck_history(deck) == {"undo": "you", "redo": None}
