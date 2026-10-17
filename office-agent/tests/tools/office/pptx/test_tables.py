from pathlib import Path

import pytest

from .helpers import (
    _tools_by_name,
)

# --- edit_pptx_table_cell / merge_pptx_table_cells (Tier 1 #2: table editing) ---


def _table_deck(tmp_path: Path, tools: dict[str, object]) -> int:
    """Writes a 3-row x 3-col table deck (header + 2 data rows), returns
    the table's shape_index."""
    content = "# Table\n| A | B | C |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |\n"
    tools["write_pptx"](path="deck.pptx", content=content)
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    return next(s["index"] for s in shapes if s["is_table"])


def test_edit_pptx_table_cell_replaces_one_cell_leaves_others_alone(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)

    result = tools["edit_pptx_table_cell"](
        path="deck.pptx", slide=1, shape_index=table_index, row=1, col=1, text="CHANGED"
    )
    assert result["row"] == 1
    assert result["col"] == 1

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table = list(prs.slides[0].shapes)[table_index].table
    assert table.cell(1, 1).text == "CHANGED"
    # Neighboring cells untouched.
    assert table.cell(1, 0).text == "1"
    assert table.cell(0, 1).text == "B"


def test_edit_pptx_table_cell_replaces_not_appends(tmp_path: Path) -> None:
    """Same real-world append-vs-replace bug class edit_pptx_text was
    fixed for -- writing to a cell that already has text must replace
    it, not garble it onto the end."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)
    tools["edit_pptx_table_cell"](
        path="deck.pptx", slide=1, shape_index=table_index, row=0, col=0, text="NEW"
    )

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table = list(prs.slides[0].shapes)[table_index].table
    assert table.cell(0, 0).text == "NEW"


def test_edit_pptx_table_cell_rejects_out_of_range_cell(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)
    with pytest.raises(ValueError, match="out of range"):
        tools["edit_pptx_table_cell"](
            path="deck.pptx", slide=1, shape_index=table_index, row=9, col=0, text="x"
        )


def test_edit_pptx_table_cell_rejects_non_table_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)
    title_index = next(
        s["index"]
        for s in tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
        if not s["is_table"]
    )
    assert title_index != table_index
    with pytest.raises(ValueError, match="isn't a table"):
        tools["edit_pptx_table_cell"](
            path="deck.pptx", slide=1, shape_index=title_index, row=0, col=0, text="x"
        )


def test_merge_pptx_table_cells_merges_a_row_span(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)

    result = tools["merge_pptx_table_cells"](
        path="deck.pptx",
        slide=1,
        shape_index=table_index,
        start_row=0,
        start_col=0,
        end_row=0,
        end_col=2,
    )
    assert result["merged_range"] == {
        "start_row": 0,
        "start_col": 0,
        "end_row": 0,
        "end_col": 2,
    }

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table = list(prs.slides[0].shapes)[table_index].table
    origin = table.cell(0, 0)
    assert origin.is_merge_origin is True
    assert origin.span_width == 3
    assert table.cell(0, 1).is_spanned is True
    assert table.cell(0, 2).is_spanned is True


def test_merge_pptx_table_cells_accepts_either_diagonal_order(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)

    tools["merge_pptx_table_cells"](
        path="deck.pptx",
        slide=1,
        shape_index=table_index,
        start_row=1,
        start_col=2,
        end_row=0,
        end_col=1,
    )

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table = list(prs.slides[0].shapes)[table_index].table
    assert table.cell(0, 1).span_width == 2
    assert table.cell(0, 1).span_height == 2


def test_merge_pptx_table_cells_rejects_out_of_range_cell(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)
    with pytest.raises(ValueError, match="out of range"):
        tools["merge_pptx_table_cells"](
            path="deck.pptx",
            slide=1,
            shape_index=table_index,
            start_row=0,
            start_col=0,
            end_row=9,
            end_col=0,
        )


def test_merge_pptx_table_cells_rejects_range_already_containing_a_merge(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path)
    table_index = _table_deck(tmp_path, tools)
    tools["merge_pptx_table_cells"](
        path="deck.pptx",
        slide=1,
        shape_index=table_index,
        start_row=0,
        start_col=0,
        end_row=0,
        end_col=1,
    )
    with pytest.raises(ValueError, match="merged cell"):
        tools["merge_pptx_table_cells"](
            path="deck.pptx",
            slide=1,
            shape_index=table_index,
            start_row=0,
            start_col=0,
            end_row=0,
            end_col=2,
        )


def test_merge_pptx_table_cells_rejects_non_table_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _table_deck(tmp_path, tools)
    title_index = next(
        s["index"]
        for s in tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
        if not s["is_table"]
    )
    with pytest.raises(ValueError, match="isn't a table"):
        tools["merge_pptx_table_cells"](
            path="deck.pptx",
            slide=1,
            shape_index=title_index,
            start_row=0,
            start_col=0,
            end_row=0,
            end_col=1,
        )
