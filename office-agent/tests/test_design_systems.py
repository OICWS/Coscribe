"""The design-system library: a store of per-person systems under the app's data directory."""

from pathlib import Path
from typing import Any

import pytest

from coscribe.tools import DesignSystemError, DesignSystemStore


def test_a_new_system_starts_with_colors_and_text_styles(tmp_path: Path) -> None:
    store = DesignSystemStore(tmp_path)
    made = store.create("Acme brand")
    assert made["name"] == "Acme brand"
    assert [c["name"] for c in made["colors"]][:2] == ["Background", "Text"]
    assert {s["id"] for s in made["typography"]["styles"]} >= {"heading-1", "body", "caption"}
    assert store.get(made["id"]) == made
    assert (tmp_path / "design_systems" / made["id"] / "system.json").is_file()


def test_the_list_is_newest_change_first(tmp_path: Path) -> None:
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
