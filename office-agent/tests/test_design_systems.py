"""The design-system library: a store of per-person systems under the app's data directory."""

from pathlib import Path
from typing import Any

import pytest

from coscribe.tools import DesignSystemError, DesignSystemStore, design_systems


def test_a_new_system_starts_with_colors_and_text_styles(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme brand")
    assert made["name"] == "Acme brand"
    assert [c["name"] for c in made["colors"]][:2] == ["Background", "Text"]
    assert {s["id"] for s in made["typography"]["styles"]} >= {"heading-1", "body", "caption"}
    assert store.get(made["id"]) == made
    assert (tmp_path / "design_systems" / made["id"] / "system.json").is_file()


def test_the_list_is_newest_change_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Windows' clock moves in steps of about 15 ms, so three quick writes can share one time.
    ticks = iter(f"2026-01-01T00:00:0{n}+00:00" for n in range(10))
    monkeypatch.setattr(design_systems, "_now", lambda: next(ticks))
    store = DesignSystemStore(tmp_path)
    first = store.create("First")
    second = store.create("Second")
    store.update(first["id"], {**first, "name": "First, renamed"})
    assert [s["name"] for s in store.list_systems()] == ["First, renamed", "Second"]
    assert store.list_systems()[1]["id"] == second["id"]


def test_saving_keeps_what_the_form_sent_and_checks_it(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    data = {
        **made,
        "overview": "Calm and technical.",
        "colors": [{"name": "Brand", "value": "#abcdef", "note": "Logo"}],
        "spacing": [{"name": "Gap", "value": "24"}],
        "radius": [{"name": "Card", "value": "16"}],
    }
    saved = store.update(made["id"], data)
    assert saved is not None
    assert saved["colors"] == [{"name": "Brand", "value": "#ABCDEF", "note": "Logo"}]
    assert saved["created_at"] == made["created_at"] and saved["updated_at"] >= made["updated_at"]
    assert store.get(made["id"]) == saved


@pytest.mark.parametrize(
    "change",
    [
        {"name": "  "},
        {"colors": [{"name": "Bad", "value": "blue", "note": ""}]},
        {"colors": "nope"},
        {"typography": {"fonts": [], "styles": [{"id": "a", "name": "A", "size": "big"}]}},
        {"overview": "x" * 20_001},
    ],
)
def test_a_system_that_cannot_be_kept_is_refused_and_nothing_changes(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    with pytest.raises(DesignSystemError):
        store.update(made["id"], {**made, **change})
    assert store.get(made["id"]) == made


def test_two_text_styles_cannot_share_an_id(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    style = made["typography"]["styles"][0]
    with pytest.raises(DesignSystemError):
        store.update(made["id"], {**made, "typography": {"fonts": [], "styles": [style, style]}})


def test_delete_removes_the_folder_and_an_id_never_names_another_path(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    (tmp_path / "outside").mkdir()
    assert store.get("../outside") is None and not store.delete("../outside")
    assert store.update("../outside", {"name": "x"}) is None
    assert store.delete(made["id"])
    assert store.get(made["id"]) is None and not store.delete(made["id"])
    assert (tmp_path / "outside").is_dir()


def test_a_listing_carries_each_systems_first_colors(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    colors = [{"name": f"c{i}", "value": f"#0000{i:02X}", "note": ""} for i in range(12)]
    store.update(made["id"], {**store.get(made["id"]), "colors": colors})

    [listed] = store.list_systems()

    assert listed["palette"] == [f"#0000{i:02X}" for i in range(8)]


def _png(width: int, height: int) -> bytes:
    from io import BytesIO

    from PIL import Image

    out = BytesIO()
    Image.new("RGB", (width, height), "#0F766E").save(out, "PNG")
    return out.getvalue()


def test_a_picture_is_kept_by_its_content_with_a_note_and_goes_with_a_duplicate(
    tmp_path: Path,
) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    logo = store.add_asset(made["id"], _png(120, 40), "acme-logo.png")
    assert logo is not None
    assert (logo["name"], logo["kind"], logo["width"], logo["height"]) == (
        "acme-logo",
        "logo",
        120,
        40,
    )
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 32"><rect/></svg>'
    mark = store.add_asset(made["id"], svg, "mark")
    assert mark is not None and (mark["file"].endswith(".svg"), mark["width"]) == (True, 64)

    noted = store.update_asset(
        made["id"], logo["id"], {"kind": "icon", "note": "on dark backgrounds"}
    )
    assert noted is not None and (noted["kind"], noted["note"], noted["name"]) == (
        "icon",
        "on dark backgrounds",
        "acme-logo",
    )
    # Saving the form keeps the pictures: they are not part of what it sends.
    store.update(made["id"], {"name": "Acme 2"})
    assert [a["id"] for a in store.get(made["id"])["assets"]] == [logo["id"], mark["id"]]

    copy = store.duplicate(made["id"], "Acme copy")
    assert copy is not None and copy["id"] != made["id"] and len(copy["assets"]) == 2
    kept = store.asset_file(copy["id"], logo["id"])
    assert kept is not None and kept[1] == "image/png" and kept[0].read_bytes() == _png(120, 40)

    assert store.delete_asset(made["id"], logo["id"])
    assert store.asset_file(made["id"], logo["id"]) is None
    assert store.asset_file(copy["id"], logo["id"]) is not None


def test_a_file_that_is_not_a_picture_too_big_or_one_too_many_is_refused(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme")
    with pytest.raises(DesignSystemError, match="SVG, PNG, JPEG or WebP"):
        store.add_asset(made["id"], b"MZ\x90\x00 not a picture", "logo.png")
    with pytest.raises(DesignSystemError, match="2 MB"):
        store.add_asset(made["id"], b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024), "big.png")
    with pytest.raises(DesignSystemError, match="is a logo, icon, picture"):
        logo = store.add_asset(made["id"], _png(4, 4), "x")
        assert logo is not None
        store.update_asset(made["id"], logo["id"], {"kind": "banner"})
    for i in range(23):
        store.add_asset(made["id"], _png(4, 4), f"p{i}")
    with pytest.raises(DesignSystemError, match="at most 24"):
        store.add_asset(made["id"], _png(4, 4), "one more")
    assert store.add_asset("not-an-id", _png(4, 4), "x") is None
