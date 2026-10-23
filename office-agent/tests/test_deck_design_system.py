"""A deck's design system: made from the deck's pages, kept once saved, and the text-style mark
a section may carry (decision 0017)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coscribe.tools import NotBuiltFromPages, design_system
from coscribe.tools.office.pptx.engine import build_deck
from coscribe.tools.office.pptx.engine.section_format import SectionError, parse_section

from .test_deck_engine import CARDS, COVER


def _deck(tmp_path: Path) -> Path:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01-cover.svg").write_text(COVER, encoding="utf-8")
    (folder / "02-cards.svg").write_text(CARDS, encoding="utf-8")
    assert build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path).ok
    return tmp_path / "deck.pptx"


def test_the_design_system_is_made_from_the_pages_and_saved(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    made = design_system(deck)
    assert [s["id"] for s in made["styles"]] == [
        "heading-1",
        "heading-3",
        "lead",
        "eyebrow",
        "body",
        "caption",
    ]
    assert made["palette"] and all(c.startswith("#") and len(c) == 7 for c in made["palette"])
    assert made["fonts"]
    assert (tmp_path / "pages" / "design-system.json").is_file()


def test_a_saved_design_system_is_kept(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    design_system(deck)
    path = tmp_path / "pages" / "design-system.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["styles"][0]["size"] = 120
    path.write_text(json.dumps(data), encoding="utf-8")
    assert design_system(deck)["styles"][0]["size"] == 120


def test_a_damaged_file_falls_back_to_the_default_without_being_overwritten(
    tmp_path: Path,
) -> None:
    deck = _deck(tmp_path)
    path = tmp_path / "pages" / "design-system.json"
    path.write_text("{not json", encoding="utf-8")
    assert design_system(deck)["styles"][0]["id"] == "heading-1"
    assert path.read_text(encoding="utf-8") == "{not json"


def test_a_deck_not_built_from_pages_has_none(tmp_path: Path) -> None:
    other = tmp_path / "other.pptx"
    other.write_bytes(b"")
    with pytest.raises(NotBuiltFromPages):
        design_system(other)


def test_a_section_may_name_a_text_style_by_its_id() -> None:
    box = 'style="left:0px;top:0px;width:9px;height:9px"'
    marked = f'<section><h1 data-text-style="heading-1" {box}>A</h1></section>'
    assert parse_section(marked)
    with pytest.raises(SectionError):
        parse_section(marked.replace("heading-1", "Heading 1"))


def test_the_fonts_are_read_from_svg_attributes_and_section_styles(tmp_path: Path) -> None:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01-cover.svg").write_text(
        COVER.replace("Microsoft YaHei, Arial", "Georgia"), encoding="utf-8"
    )
    deck = tmp_path / "deck.pptx"
    assert build_deck(folder, deck, resource_root=tmp_path).ok
    assert design_system(deck)["fonts"][0] == "Georgia"


def test_a_seed_is_the_decks_first_design_system_and_then_the_decks_own(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    seed = {
        "name": "Acme",
        "palette": ["#112233"],
        "fonts": ["Inter"],
        "styles": [
            {
                "id": "body",
                "name": "Body",
                "size": 30,
                "weight": 400,
                "line_height": 1.4,
                "letter_spacing": 0,
            }
        ],
        "overview": "Calm.",
    }
    made = design_system(deck, seed)
    assert made["palette"] == ["#112233"] and made["overview"] == "Calm."
    # Once saved, a different seed does not replace it.
    assert design_system(deck, {**seed, "palette": ["#ffffff"]})["palette"] == ["#112233"]
    # A seed that is not a design system is ignored, not saved.
    other = tmp_path / "other"
    other.mkdir()
    assert design_system(_deck(other), {"name": "bad"})["palette"] != []
