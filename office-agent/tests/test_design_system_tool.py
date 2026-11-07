from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from coscribe.tools import DesignSystemError, DesignSystemStore, build_design_system_tools


def _save(tmp_path: Path) -> Any:
    return build_design_system_tools(tmp_path)[0]


def test_a_new_system_starts_from_the_defaults_and_takes_what_is_given(tmp_path: Path) -> None:
    result = _save(tmp_path)(
        name="Acme",
        overview="Calm and technical.",
        colors=[{"name": "Ink", "value": "#112233", "note": "Text"}],
        fonts=["Inter"],
    )
    saved = DesignSystemStore(tmp_path).get(result["id"])
    assert saved is not None
    assert saved["name"] == "Acme" and saved["overview"] == "Calm and technical."
    assert saved["colors"] == [{"name": "Ink", "value": "#112233", "note": "Text"}]
    assert saved["typography"]["fonts"] == ["Inter"]
    assert len(saved["typography"]["styles"]) == 6
    assert result["summary"].startswith("1 colors, 1 fonts, 6 text styles")


def test_an_id_changes_only_the_fields_passed(tmp_path: Path) -> None:
    save = _save(tmp_path)
    made = save(name="Acme", overview="Calm.", fonts=["Inter"])
    save(system_id=made["id"], colors=[{"name": "Warm", "value": "#aa5500", "note": ""}])
    saved = DesignSystemStore(tmp_path).get(made["id"])
    assert saved is not None
    assert saved["colors"][0]["value"] == "#AA5500"
    assert saved["overview"] == "Calm." and saved["typography"]["fonts"] == ["Inter"]
    assert len(DesignSystemStore(tmp_path).list_systems()) == 1


def test_a_bad_value_is_refused_and_leaves_no_half_made_system(tmp_path: Path) -> None:
    with pytest.raises(DesignSystemError, match="not a color"):
        _save(tmp_path)(name="Acme", colors=[{"name": "Ink", "value": "blue"}])
    assert DesignSystemStore(tmp_path).list_systems() == []


def test_a_bad_value_on_an_existing_system_keeps_it_as_it_was(tmp_path: Path) -> None:
    save = _save(tmp_path)
    made = save(name="Acme")
    with pytest.raises(DesignSystemError):
        save(system_id=made["id"], spacing=[{"name": 3}])
    assert DesignSystemStore(tmp_path).get(made["id"]) is not None


def test_a_new_system_needs_a_name_and_an_id_must_exist(tmp_path: Path) -> None:
    save = _save(tmp_path)
    with pytest.raises(DesignSystemError, match="needs a name"):
        save(overview="x")
    with pytest.raises(DesignSystemError, match="no design system"):
        save(system_id="0123456789", name="x")


def _png(width: int, height: int, colour: str = "#0F766E") -> bytes:
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(out, "PNG")
    return out.getvalue()


def test_pictures_the_user_attached_are_added_once_each(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_bytes(_png(40, 20))
    (tmp_path / "mark.png").write_bytes(_png(16, 16, "#F59E0B"))
    save = build_design_system_tools(tmp_path / "state", tmp_path)[0]
    made = save(name="Acme", assets=[{"file": "logo.png", "kind": "logo", "note": "light"}])

    again = save(
        system_id=made["id"],
        assets=[{"file": "logo.png", "kind": "logo"}, {"file": "mark.png", "kind": "icon"}],
    )

    assets = DesignSystemStore(tmp_path / "state").get(made["id"])["assets"]
    assert [(a["name"], a["kind"], a["note"]) for a in assets] == [
        ("logo", "logo", "light"),
        ("mark", "icon", ""),
    ]
    assert again["summary"].endswith(", 2 pictures")


def test_a_picture_that_cant_be_taken_leaves_no_half_made_system(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("not a picture", encoding="utf-8")
    save = build_design_system_tools(tmp_path / "state", tmp_path)[0]
    for file, problem in (
        ("notes.txt", "SVG, PNG, JPEG or WebP"),
        ("gone.png", "not a file that can be read"),
        ("../outside.png", "not a file that can be read"),
        ("notes.txt#word/media/image1.png", "deck.pptx#ppt/media"),
    ):
        with pytest.raises(DesignSystemError, match=problem):
            save(name="Acme", assets=[{"file": file, "kind": "logo"}])
    with pytest.raises(DesignSystemError, match="add them in Settings"):
        _save(tmp_path / "other")(name="Acme", assets=[{"file": "logo.png"}])
    assert DesignSystemStore(tmp_path / "state").list_systems() == []
