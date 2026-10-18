"""Property test for the Slides panel's arrangement and undo (assessment §4.5): any sequence of
new, copy, move, delete, save and comment on a small deck leaves the deck consistent after every
step, and undoing every step brings back the first pages byte for byte.

Hypothesis picks the sequence and the indices; an index is taken modulo the slides there are, so
every step is meaningful. Each step builds the deck, so the examples are few and short.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pptx import Presentation

from coscribe.tools.office.pptx import (
    add_comment,
    delete_slide,
    duplicate_slide,
    insert_slide,
    move_slide,
    read_comments,
    read_deck,
    save_slide,
    slide_parts,
    step_history,
)
from coscribe.tools.office.pptx.engine import build_deck

from .test_deck_arrange import NEW
from .test_deck_engine import CARDS, COVER

_SETTINGS = settings(
    deadline=None,
    derandomize=True,
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow],
)
# A step is a kind and two numbers; fifty states are kept for undo, so a run stays well under.
_STEPS = st.lists(
    st.tuples(
        st.sampled_from(["insert", "copy", "move", "delete", "save", "comment"]),
        st.integers(0, 9),
        st.integers(0, 9),
    ),
    min_size=1,
    max_size=10,
)
_TRANSITIONS = ["fade", "push", "magic"]


def _pages(folder: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.suffix in (".svg", ".html")}


def _check(deck: Path, folder: Path) -> list[str]:
    """What must hold after every step; returns the slides' names."""
    info = read_deck(deck)
    names = [s["name"] for s in info["slides"]]
    width = max(2, len(str(len(names))))
    assert [n.split("-")[0] for n in names] == [f"{i:0{width}d}" for i in range(1, len(names) + 1)]
    assert not info["changed"]
    assert len(Presentation(str(deck)).slides) == len(names)
    assert not list(folder.glob(".arranging-*"))
    stems = {Path(n).stem for n in names}
    assert {c["slide"] for c in read_comments(deck)} <= stems
    return names


def _step(deck: Path, root: Path, kind: str, a: int, b: int) -> None:
    count = len(read_deck(deck)["slides"])
    index = a % count
    if kind == "insert":
        insert_slide(deck, index - 1 if b % 2 else index, NEW, resource_root=root)
    elif kind == "copy":
        duplicate_slide(deck, index, resource_root=root)
    elif kind == "move":
        move_slide(deck, index, b % count, resource_root=root)
    elif kind == "delete":
        if count == 1:
            with pytest.raises(ValueError):
                delete_slide(deck, index, resource_root=root)
        else:
            delete_slide(deck, index, resource_root=root)
    elif kind == "save":
        read = slide_parts(deck, index, root)
        source = re.sub(r' data-transition="[^"]*"', "", read["source"], count=1)
        source = source.replace("<section", f'<section data-transition="{_TRANSITIONS[b % 3]}"', 1)
        save_slide(deck, index, source=source, version=read["version"], resource_root=root)
    else:
        name = read_deck(deck)["slides"][index]["name"]
        add_comment(
            deck,
            slide=Path(name).stem,
            x=0.5,
            y=0.5,
            element="",
            author="ana",
            text=f"note {b}",
            sent=False,
        )


@_SETTINGS
@given(steps=_STEPS)
def test_any_sequence_of_arranging_leaves_the_deck_consistent_and_undoes_to_the_start(
    steps: list[tuple[str, int, int]],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        folder = root / "pages"
        folder.mkdir()
        (folder / "01-cover.svg").write_text(COVER, encoding="utf-8")
        (folder / "02-cards.svg").write_text(CARDS, encoding="utf-8")
        deck = root / "deck.pptx"
        assert build_deck(folder, deck, resource_root=root).ok
        first = _pages(folder)

        for kind, a, b in steps:
            _step(deck, root, kind, a, b)
            _check(deck, folder)

        while True:
            try:
                step_history(deck, -1, resource_root=root)
            except ValueError:
                break
            _check(deck, folder)
        assert _pages(folder) == first
