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

import contextlib
import difflib
import os
import shutil
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


# Committed files, not written by Pillow at test time: a PNG's bytes depend on the encoder and
# the zlib it links, which can differ between machines and versions.
ASSETS = GOLDEN_DIR / "assets"


def _png(name: str) -> None:
    shutil.copyfile(ASSETS / name, name)


def _image(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](path="deck.pptx", content="# Our logo\n- placed top right")
    _png("logo.png")
    tools["add_pptx_image"](
        path="deck.pptx", slide=1, image_path="logo.png", left=8.0, top=0.5, width=2.0
    )


def _picture_index(tools: dict[str, Callable[..., object]]) -> int:
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]  # type: ignore[index]
    return next(shape["index"] for shape in shapes if shape["is_picture"])


def _image_cropped_and_replaced(tools: dict[str, Callable[..., object]]) -> None:
    _image(tools)
    index = _picture_index(tools)
    tools["crop_pptx_image"](
        path="deck.pptx", slide=1, shape_index=index, crop_left=0.1, crop_right=0.2
    )
    _png("logo2.png")
    tools["replace_pptx_image"](
        path="deck.pptx", slide=1, shape_index=index, image_path="logo2.png"
    )


def _image_effects(tools: dict[str, Callable[..., object]]) -> None:
    _image(tools)
    index = _picture_index(tools)
    for effect in ("soft_edge", "shadow", "glow"):
        tools["add_pptx_shape_effect"](path="deck.pptx", slide=1, shape_index=index, effect=effect)


def _background_image(tools: dict[str, Callable[..., object]]) -> None:
    tools["write_pptx"](path="deck.pptx", content="# Over a photo\n- with a scrim")
    _png("photo.png")
    tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="photo.png")
    tools["add_pptx_scrim"](path="deck.pptx", slide=1, opacity=0.4, color="000000")


DECKS: dict[str, Callable[[dict[str, Callable[..., object]]], None]] = {
    "background_image": _background_image,
    "bullets": _bullets,
    "image": _image,
    "image_cropped_and_replaced": _image_cropped_and_replaced,
    "image_effects": _image_effects,
    "table": _table,
    "two_column": _two_column,
    "transition_and_animation": _transition_and_animation,
    "theme": _theme,
}


def build_deck(name: str, root: Path) -> Path:
    """Build deck `name` in `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    # Builders copy their source images next to the deck, by relative path.
    with contextlib.chdir(root):
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
