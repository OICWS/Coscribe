"""Golden (characterization) tests of the XML the pptx tools write.

`tools/presentations.py` is to be split into a package by pure moves (the scale assessment,
step 11). A pure move must leave every file the tools write unchanged, and these tests are
how that is shown: each deck is built through the public tools, reduced to canonical text
(`tests/pptx_canonical.py`), and compared with a checked-in golden under
`tests/golden/pptx/`. A change that alters what a deck contains edits its golden in the same
pull request, so the reviewer sees the XML that changed.
`UPDATE_GOLDENS=1 pytest tests/test_office_golden.py` rewrites them; read the diff before
committing it.
"""

from __future__ import annotations

import difflib
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from coscribe.tools.presentations import build_presentation_tools

from .pptx_canonical import canonical_text

GOLDEN_DIR = Path(__file__).parent / "golden" / "pptx"


def _tools(root: Path) -> dict[str, Callable[..., object]]:
    return {tool.__name__: tool for tool in build_presentation_tools(root)}  # type: ignore[attr-defined]


def _bullets(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](
        path="deck.pptx",
        content="# Quarterly review\n- Revenue up 12%\n- **Two** new markets\n- *Hiring* on track",
    )


def _table(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](
        path="deck.pptx",
        content="# Results\n| Region | Q1 | Q2 |\n| --- | --- | --- |\n| North | 10 | 12 |\n"
        "| South | 8 | 9 |",
    )


def _two_column(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](
        path="deck.pptx",
        content="layout: two-column\n# Before vs after\n- Manual tracking\n- No alerts\n>>>\n"
        "- Live dashboards\n- Proactive alerts",
    )


def _transition_and_animation(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](path="deck.pptx", content="# Intro\n- one\n- two\n\n---\n# Next\n- three")
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade", duration=0.8)
    tools["add_pptx_animation"](path="deck.pptx", slide=2, shape_index=0, animation="fade")


def _theme(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](
        path="deck.pptx", content="# Dark deck\n- body text", theme="bg=111827,text=F8FAFC"
    )
    tools["edit_pptx_theme_colors"](path="deck.pptx", colors="accent1=0F6B5C,accent2=C2410C")


DECKS: dict[str, Callable[[dict[str, Callable[..., object]]], None]] = {
    "bullets": _bullets,
    "table": _table,
    "two_column": _two_column,
    "transition_and_animation": _transition_and_animation,
    "theme": _theme,
}


def build_deck(name: str, root: Path) -> Path:
    """Build deck `name` in `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    DECKS[name](_tools(root))
    return root / "deck.pptx"


@pytest.fixture(autouse=True)
def _no_libreoffice(monkeypatch: pytest.MonkeyPatch) -> None:
    # The LibreOffice QA pass only reads the deck; skipping it keeps these tests fast and the
    # same on machines with and without LibreOffice.
    monkeypatch.setattr("shutil.which", lambda name: None)


@pytest.mark.parametrize("name", sorted(DECKS))
def test_deck_matches_its_golden(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    actual = canonical_text(build_deck(name, tmp_path / name))
    golden = GOLDEN_DIR / f"{name}.txt"
    if os.environ.get("UPDATE_GOLDENS") == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(actual, encoding="utf-8", newline="\n")
    expected = golden.read_text(encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            f"golden/pptx/{name}.txt",
            "built now",
            n=2,
        )
    )
    assert actual == expected, (
        f"deck {name!r} differs from its golden; if the change is intended, run "
        f"UPDATE_GOLDENS=1 pytest tests/test_office_golden.py and commit the diff:\n{diff[:4000]}"
    )


def test_every_golden_belongs_to_a_deck() -> None:
    stale = sorted(path.stem for path in GOLDEN_DIR.glob("*.txt") if path.stem not in DECKS)
    assert stale == [], f"goldens with no deck that builds them: {stale}"
