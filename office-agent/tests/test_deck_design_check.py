"""A deck that began from a system of the person's library warns about what its pages use that
the system does not have (decision 0020): the system guides, it does not forbid."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from coscribe.tools import DesignSystemStore
from coscribe.tools.office.pptx import build_presentation_tools
from coscribe.tools.office.pptx.engine import build_deck
from coscribe.tools.office.pptx.engine.design_check import off_system, unplaced_logo

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


LOGO = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20">'
    b'<rect width="40" height="20"/></svg>'
)
WITH_LOGO = {
    **SYSTEM,
    "assets": [
        {
            "kind": "logo",
            "name": "logo",
            "note": "on light backgrounds",
            "path": "brand/Acme/logo.svg",
            "sha256": hashlib.sha256(LOGO).hexdigest(),
        },
        {"kind": "icon", "name": "app icon", "path": "brand/Acme/app-icon.svg", "sha256": "0" * 64},
    ],
}


def _picture(src: str) -> str:
    return (
        f'<section><img src="{src}" style="left:100px;top:100px;width:200px;height:100px;'
        'object-fit:contain"/></section>'
    )


def test_a_logo_counts_as_placed_by_its_file_whatever_it_is_called(tmp_path: Path) -> None:
    (tmp_path / "mark.svg").write_bytes(LOGO)
    (tmp_path / "redrawn.svg").write_bytes(LOGO.replace(b"<rect", b"<rect fill='#FF0000'"))

    assert unplaced_logo(WITH_LOGO, tmp_path, [("01.html", _picture("mark.svg"))]) is None
    warning = unplaced_logo(WITH_LOGO, tmp_path, [("01.html", _picture("redrawn.svg"))])
    assert warning is not None
    assert "brand/Acme/logo.svg (on light backgrounds)" in warning and "app-icon" not in warning
    assert unplaced_logo(SYSTEM, tmp_path, [("01.html", _section("#2563EB"))]) is None


def test_the_first_build_checks_the_deck_against_the_conversations_system(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path / "state")
    made = store.create("Acme")
    asset = store.add_asset(made["id"], LOGO, "logo.svg")
    assert asset is not None
    store.update_asset(made["id"], asset["id"], {"kind": "logo", "note": "on light backgrounds"})
    store.choose_for_thread("t1", made["id"])
    workspace = tmp_path / "workspace"
    folder = workspace / "pages"
    folder.mkdir(parents=True)
    (folder / "01.html").write_text(_section("#2563EB"), encoding="utf-8")
    tools = build_presentation_tools(workspace, state_dir=tmp_path / "state", thread_id="t1")
    build = next(t for t in tools if t.__name__ == "build_pptx_from_pages")

    unplaced = build("pages", "deck.pptx")
    (folder / "mark.svg").write_bytes(LOGO)
    (folder / "02.html").write_text(_picture("mark.svg"), encoding="utf-8")
    placed = build("pages", "deck.pptx")

    kept = json.loads((folder / "design-system.json").read_text(encoding="utf-8"))
    assert kept["source"] == made["id"]
    assert any("brand/Acme/logo.svg" in w for w in unplaced["warnings"])
    assert placed["ok"] and placed["slides"] == 2  # mark.svg is a picture, not a slide
    assert not any("logo" in w for w in placed.get("warnings", []))
