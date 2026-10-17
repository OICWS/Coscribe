from pathlib import Path

import pytest

from .helpers import (
    _tools_by_name,
)

# --- add_pptx_shape / list_pptx_shape_types (Tier 2: diagram-building shapes) ---


def test_list_pptx_shape_types_returns_sorted_known_names(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    names = tools["list_pptx_shape_types"]()
    assert names == sorted(names)
    assert "RIGHT_ARROW" in names
    assert "FLOWCHART_DECISION" in names
    assert "ROUNDED_RECTANGLE" in names


def test_add_pptx_shape_adds_shape_with_position_size_and_text(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")

    result = tools["add_pptx_shape"](
        path="deck.pptx",
        slide=1,
        shape_type="RIGHT_ARROW",
        left_in=1.0,
        top_in=2.0,
        width_in=3.0,
        height_in=1.5,
        text="Next **step**",
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shapes = list(prs.slides[0].shapes)
    shape = shapes[result["shape_index"]]
    assert shape.auto_shape_type == MSO_SHAPE.RIGHT_ARROW
    assert shape.left == 914400
    assert shape.top == 1828800
    assert shape.width == 2743200
    assert shape.height == 1371600
    assert shape.text_frame.text == "Next step"
    assert shape.text_frame.paragraphs[0].runs[1].font.bold is True


def test_add_pptx_shape_sets_fill_and_line_color(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.dml import MSO_COLOR_TYPE

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")

    result = tools["add_pptx_shape"](
        path="deck.pptx",
        slide=1,
        shape_type="FLOWCHART_DECISION",
        left_in=1.0,
        top_in=1.0,
        width_in=2.0,
        height_in=2.0,
        fill_color="38BDF8",
        line_color="0F172A",
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[result["shape_index"]]
    assert shape.fill.fore_color.type == MSO_COLOR_TYPE.RGB
    assert str(shape.fill.fore_color.rgb) == "38BDF8"
    assert str(shape.line.color.rgb) == "0F172A"


def test_add_pptx_shape_returned_index_targets_the_right_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")

    result = tools["add_pptx_shape"](
        path="deck.pptx",
        slide=1,
        shape_type="OVAL",
        left_in=1.0,
        top_in=1.0,
        width_in=1.0,
        height_in=1.0,
    )

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert shapes[result["shape_index"]]["shape_type"] is not None
    assert shapes[result["shape_index"]]["left_in"] == 1.0


def test_add_pptx_shape_rejects_unknown_shape_type(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    with pytest.raises(ValueError, match="Unknown shape_type"):
        tools["add_pptx_shape"](
            path="deck.pptx",
            slide=1,
            shape_type="NOT_A_REAL_SHAPE",
            left_in=1.0,
            top_in=1.0,
            width_in=1.0,
            height_in=1.0,
        )


def test_add_pptx_shape_rejects_bad_fill_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    with pytest.raises(ValueError, match="6-hex-digit color"):
        tools["add_pptx_shape"](
            path="deck.pptx",
            slide=1,
            shape_type="OVAL",
            left_in=1.0,
            top_in=1.0,
            width_in=1.0,
            height_in=1.0,
            fill_color="#38BDF8",
        )
