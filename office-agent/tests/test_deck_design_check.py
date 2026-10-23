"""A deck that began from a system of the person's library warns about what its pages use that
the system does not have (decision 0020): the system guides, it does not forbid."""

from __future__ import annotations

import json
from pathlib import Path

from coscribe.tools.office.pptx.engine import build_deck
from coscribe.tools.office.pptx.engine.design_check import off_system

SYSTEM = {
    "name": "Acme",
    "source": "ab12cd34ef",
    "palette": ["#1F2937", "#2563EB"],
    "fonts": ["Inter"],
    "styles": [{"id": "body"}, {"id": "heading-1"}],
}


def _section(colour: str, font: str = "Inter", style: str = "body") -> str:
    return (
        f'<section><p data-text-style="{style}" style="left:100px;top:100px;width:900px;'
        f'height:120px;font-size:32px;color:{colour};font-family:{font}">Hello</p></section>'
    )


def test_a_colour_font_or_style_outside_the_system_is_named() -> None:
    found = off_system(SYSTEM, [("01.html", _section("#FF00AA", "Comic Sans MS", "fancy"))])

    assert found["01.html"] == [
        "off the design system: #FF00AA (nearest #2563EB) not in the design system 'Acme''s colors",
        "off the design system: 'Comic Sans MS' not among the design system's fonts (inter)",
        "off the design system: 'fancy' not a text style of the design system",
    ]


def test_what_the_system_has_or_is_close_to_is_not_named() -> None:
    page = _section("#2563EB") + _section("#1f2938") + _section("#FFFFFF")  # exact, near, neutral

    assert off_system(SYSTEM, [("01.html", page.replace("Inter", "sans-serif"))]) == {}


def test_many_strays_are_counted_not_all_listed() -> None:
    page = "".join(_section(f"#{n:02X}0000") for n in range(0x30, 0x38))

    [line] = off_system(SYSTEM, [("01.html", page)])["01.html"]

    assert "and 4 more" in line


def test_a_build_carries_the_warnings_of_a_deck_from_the_library(tmp_path: Path) -> None:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01.html").write_text(_section("#FF00AA"), encoding="utf-8")
    (folder / "design-system.json").write_text(json.dumps(SYSTEM), encoding="utf-8")

    report = build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path)

    assert report.ok
    assert any("#FF00AA" in w for w in report.pages[0].warnings)


def test_a_deck_with_a_system_of_its_own_is_not_checked(tmp_path: Path) -> None:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01.html").write_text(_section("#FF00AA"), encoding="utf-8")
    (folder / "design-system.json").write_text(
        json.dumps({**SYSTEM, "source": None}), encoding="utf-8"
    )

    report = build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path)

    assert not any("design system" in w for w in report.pages[0].warnings)
