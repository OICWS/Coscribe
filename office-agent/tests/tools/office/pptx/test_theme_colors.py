from pathlib import Path
from typing import cast

import pytest

from .helpers import (
    _tools_by_name,
)


def test_read_pptx_theme_colors_returns_all_12_stock_slots(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    result = tools["read_pptx_theme_colors"](path="deck.pptx")
    assert result["path"] == "deck.pptx"
    colors = result["colors"]
    assert set(colors) == {
        "dk1",
        "lt1",
        "dk2",
        "lt2",
        "accent1",
        "accent2",
        "accent3",
        "accent4",
        "accent5",
        "accent6",
        "hlink",
        "folHlink",
    }
    # Stock python-pptx theme's own known default accent1.
    assert colors["accent1"] == "4F81BD"
    assert all(value is not None for value in colors.values())


def test_edit_pptx_theme_colors_changes_only_named_slots(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    before = tools["read_pptx_theme_colors"](path="deck.pptx")["colors"]

    result = tools["edit_pptx_theme_colors"](
        path="deck.pptx", colors="accent1=0F6B5C,accent2=C2410C,hlink=0F6B5C"
    )
    assert result["colors"] == {"accent1": "0F6B5C", "accent2": "C2410C", "hlink": "0F6B5C"}

    after = tools["read_pptx_theme_colors"](path="deck.pptx")["colors"]
    assert after["accent1"] == "0F6B5C"
    assert after["accent2"] == "C2410C"
    assert after["hlink"] == "0F6B5C"
    # Every other slot is untouched.
    untouched = ("dk1", "lt1", "dk2", "lt2", "accent3", "accent4", "accent5", "accent6", "folHlink")
    for slot in untouched:
        assert after[slot] == before[slot]


def test_edit_pptx_theme_colors_applies_to_every_slide_master(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["edit_pptx_theme_colors"](path="deck.pptx", colors="accent1=0F6B5C")

    prs = Presentation(tmp_path / "deck.pptx")
    for master in prs.slide_masters:
        theme_part = master.part.part_related_by(RT.THEME)
        assert b"0F6B5C" in theme_part.blob


def test_edit_pptx_theme_colors_survives_round_trip(tmp_path: Path) -> None:
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["edit_pptx_theme_colors"](path="deck.pptx", colors="accent1=0F6B5C")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Presentation(str(tmp_path / "deck.pptx"))
    colors = cast("dict[str, object]", tools["read_pptx_theme_colors"](path="deck.pptx")["colors"])
    assert colors["accent1"] == "0F6B5C"


def test_edit_pptx_theme_colors_on_real_bundled_template(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "\n---\n".join(
        ["# Title\nSubtitle", "# First\n- a", "# Second\n- b", "# Closing\nThanks"]
    )
    tools["fill_pptx_template"](path="deck.pptx", template_id="bold-statement", content=content)

    tools["edit_pptx_theme_colors"](path="deck.pptx", colors="accent1=0F6B5C")
    after = tools["read_pptx_theme_colors"](path="deck.pptx")["colors"]
    assert after["accent1"] == "0F6B5C"


def test_edit_pptx_theme_colors_rejects_unknown_slot(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="Unknown theme color slot"):
        tools["edit_pptx_theme_colors"](path="deck.pptx", colors="notaslot=FFFFFF")


def test_edit_pptx_theme_colors_rejects_bad_hex(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="6-hex-digit"):
        tools["edit_pptx_theme_colors"](path="deck.pptx", colors="accent1=zzzzzz")


def test_edit_pptx_theme_colors_rejects_empty_colors(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="must not be empty"):
        tools["edit_pptx_theme_colors"](path="deck.pptx", colors="")


def test_edit_pptx_theme_colors_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["edit_pptx_theme_colors"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


def test_read_pptx_theme_colors_is_low_risk(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["read_pptx_theme_colors"])
    assert metadata.requires_approval is False
