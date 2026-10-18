"""The engine-neutral block and object operations (decision 0011): parsing, the openpyxl
engine, the guard against lossy edits and the checker. Nothing here is offered to the model yet."""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path
from typing import Any

import pytest
from openpyxl import Workbook, load_workbook

from coscribe.tools.office.xlsx.blocks import parse_blocks, parse_ops
from coscribe.tools.office.xlsx.build import modify_workbook, write_cells

_SPARKLINES = (
    '<extLst><ext uri="{05C60535-1F16-4fd2-B633-F4F36F0B64E0}" '
    'xmlns:x14="http://schemas.microsoft.com/office/spreadsheetml/2009/9/main">'
    '<x14:sparklineGroups xmlns:xm="http://schemas.microsoft.com/office/excel/2006/main">'
    "<x14:sparklineGroup><x14:sparklines><x14:sparkline><xm:f>Data!B2:B4</xm:f>"
    "<xm:sqref>C2</xm:sqref></x14:sparkline></x14:sparklines></x14:sparklineGroup>"
    "</x14:sparklineGroups></ext></extLst></worksheet>"
)


def _table(path: Path) -> Path:
    """A user's small table: a styled header and money in column B."""
    from openpyxl.styles import Font

    book = Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append(["Item", "Amount"])
    sheet["A1"].font = sheet["B1"].font = Font(bold=True)
    for item, amount in [("Rent", 1500), ("Food", 320), ("Travel", 80)]:
        sheet.append([item, amount])
    for row in range(2, 5):
        sheet.cell(row, 2).number_format = '"$"#,##0'
    book.save(path)
    return path


def _with_sparklines(path: Path) -> Path:
    patched = path.with_name("sparkline.xlsx")
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(patched, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(b"</worksheet>", _SPARKLINES.encode())
            target.writestr(item, data)
    return patched


# --- parsing -----------------------------------------------------------------------------


def test_a_cell_takes_the_block_column_row_and_own_styles_in_that_order() -> None:
    (block,) = parse_blocks(
        [
            {
                "sheet": "S",
                "at": "B2",
                "style": {"size": 10},
                "col_styles": [{"num": "0.0"}],
                "row_styles": ["head"],
                "rows": [[{"v": 1, "s": {"color": "#ff0000"}}]],
            }
        ],
        styles={"head": {"bold": True, "num": "0%"}},
    )

    assert (block.row, block.col) == (2, 2)
    assert block.cells[0][0].style == {"size": 10, "num": "0%", "bold": True, "color": "FF0000"}


def test_formulas_are_normalised_and_a_formula_object_gets_its_equals_sign() -> None:
    (block,) = parse_blocks([{"sheet": "S", "rows": [["=XLOOKUP(1,A:A,B:B)", {"f": "A1*2"}]]}])

    assert [cell.value for cell in block.cells[0]] == ["=_xlfn.XLOOKUP(1,A:A,B:B)", "=A1*2"]


def test_an_iso_date_becomes_a_real_date_and_other_text_stays_text() -> None:
    (block,) = parse_blocks([{"sheet": "S", "rows": [["2026-01-05", "2026-01-05 09:30", "5 Jan"]]}])

    assert [cell.value for cell in block.cells[0]] == [
        dt.date(2026, 1, 5),
        dt.datetime(2026, 1, 5, 9, 30),
        "5 Jan",
    ]


@pytest.mark.parametrize(
    ("blocks", "message"),
    [
        ([{"sheet": "S", "rows": [[1]], "style": {"glow": True}}], "unknown or invalid"),
        ([{"sheet": "S", "rows": [[1]], "style": "nope"}], "no style named"),
        ([{"sheet": "a/b", "rows": [[1]]}], "sheet name"),
        ([{"sheet": "S", "at": "B0", "rows": [[1]]}], "not a cell address"),
        ([{"sheet": "S", "rows": [[{"v": 1, "f": "=1"}]]}], "`v` or `f`"),
        ([{"sheet": "S", "at": "A5", "rows": [[1], [2]], "fill_down_to": 5}], "below"),
        ([{"sheet": "S", "rows": [["=FILTER(A:A,B:B>1)"]]}], "FILTER"),
        ([{"sheet": "S", "rows": [[1]], "like": "A1", "like_row": 1}], "`like_row`"),
        ([{"sheet": "S", "rows": [["2026-02-30"]]}], "not one"),
        ([{"sheet": "S", "rows": [[1]], "row_styles": "head"}], "by position"),
    ],
)
def test_a_bad_block_is_refused_before_anything_is_written(blocks: list, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_blocks(blocks)


@pytest.mark.parametrize(
    ("ops", "message"),
    [
        ([{"op": "chart", "sheet": "S", "kind": "donut", "source": "A1:B3", "at": "D2"}], "kind"),
        ([{"op": "chart", "sheet": "S", "kind": "line"}], "missing"),
        ([{"op": "freeze", "sheet": "S", "colour": "red"}], "unknown"),
        ([{"op": "validation", "sheet": "S", "range": "C2"}], "`list`"),
        ([{"op": "explode"}], "`op` is one of"),
    ],
)
def test_a_bad_operation_is_refused(ops: list, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_ops(ops)


# --- writing -----------------------------------------------------------------------------


def test_a_new_workbook_gets_its_values_styles_and_notes(tmp_path: Path) -> None:
    path = tmp_path / "new.xlsx"

    report = write_cells(
        path,
        [
            {
                "sheet": "Summary",
                "row_styles": [{"bold": True, "fill": "1F3864", "color": "FFFFFF"}],
                "rows": [["Region", "Sales"], ["East", {"v": 1200, "note": "From the ERP"}]],
            }
        ],
    )

    sheet = load_workbook(path)["Summary"]
    assert report["saved_as_copy"] is False
    assert load_workbook(path).sheetnames == ["Summary"]
    assert sheet["A1"].font.bold and sheet["A1"].fill.fgColor.rgb.endswith("1F3864")
    assert sheet["B2"].value == 1200 and sheet["B2"].comment.text == "From the ERP"


def test_a_workbook_with_a_note_still_gets_its_formula_values(tmp_path: Path) -> None:
    path = tmp_path / "noted.xlsx"

    report = write_cells(
        path,
        [
            {
                "sheet": "S",
                "rows": [[{"v": 2, "note": "a note"}, 3, "=A1+B1"]],
            }
        ],
    )

    assert report["formula_results"] == {"S!C1": 5}
    assert load_workbook(path, data_only=True)["S"]["C1"].value == 5
    assert load_workbook(path)["S"]["A1"].comment.text == "a note"


def test_a_text_cell_that_reads_like_a_formula_is_not_listed_as_one(tmp_path: Path) -> None:
    path = tmp_path / "text.xlsx"

    report = write_cells(
        path, [{"sheet": "S", "rows": [[{"v": "=001", "text": True}, 4, "=B1*2"]]}]
    )

    assert report["formula_results"] == {"S!C1": 8}
    assert report["formulas_not_listed"] == 0


def test_cells_that_hold_something_else_are_not_overwritten_unless_asked(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.xlsx")
    block = [{"sheet": "Data", "at": "B2", "rows": [[1600]]}]

    with pytest.raises(ValueError, match="already hold"):
        write_cells(path, block)
    write_cells(path, [{"sheet": "Data", "at": "B2", "rows": [[1500]]}])
    write_cells(path, block, overwrite=True)

    assert load_workbook(path)["Data"]["B2"].value == 1600


def test_fill_down_moves_each_formula_with_its_row_and_like_copies_a_cells_look(
    tmp_path: Path,
) -> None:
    path = _table(tmp_path / "t.xlsx")

    write_cells(
        path,
        [{"sheet": "Data", "at": "C2", "like": "B2", "rows": [["=B2*2"]], "fill_down_to": 4}],
    )

    sheet = load_workbook(path)["Data"]
    assert [sheet.cell(r, 3).value for r in (2, 3, 4)] == ["=B2*2", "=B3*2", "=B4*2"]
    assert sheet["C4"].number_format == '"$"#,##0'


def test_an_edit_saves_the_users_file_with_openpyxl_and_recalculates_on_open(
    tmp_path: Path,
) -> None:
    path = _table(tmp_path / "t.xlsx")

    write_cells(path, [{"sheet": "Data", "at": "A5", "like_row": 4, "rows": [["Gym", 45]]}])

    with zipfile.ZipFile(path) as archive:
        assert b'fullCalcOnLoad="1"' in archive.read("xl/workbook.xml")


def test_an_edit_that_would_lose_sparklines_goes_to_a_copy(tmp_path: Path) -> None:
    path = _with_sparklines(_table(tmp_path / "t.xlsx"))
    original = path.read_bytes()

    report = write_cells(path, [{"sheet": "Data", "at": "A5", "rows": [["Gym", 45]]}])

    assert path.read_bytes() == original
    assert report["saved_as_copy"] is True
    assert Path(report["path"]).name == "sparkline (coscribe).xlsx"
    assert any("Sparkline" in lost for lost in report["lost_if_saved_over_original"])


def test_the_objects_land_where_the_operations_say(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.xlsx")

    modify_workbook(
        path,
        [
            {"op": "add_sheet", "name": "Lists", "tab_color": "00B050"},
            {
                "op": "chart",
                "sheet": "Data",
                "kind": "column",
                "source": "A1:B4",
                "at": "E2",
                "title": "Spend",
                "colors": ["1F3864"],
            },
            {"op": "conditional", "sheet": "Data", "range": "B2:B4", "rule": "data_bar"},
            {"op": "validation", "sheet": "Data", "range": "C2:C4", "list": ["Yes", "No"]},
            {"op": "print", "sheet": "Data", "landscape": True, "fit_width": 1},
            {"op": "freeze", "sheet": "Data", "at": "A2"},
            {"op": "name", "name": "Total", "ref": "Data!$B$2:$B$4"},
            {"op": "cols", "sheet": "Data", "cols": "A", "width": 20},
        ],
    )

    book = load_workbook(path)
    sheet = book["Data"]
    assert book.sheetnames == ["Data", "Lists"]
    assert len(sheet._charts) == 1 and sheet.freeze_panes == "A2"
    assert sheet.conditional_formatting and sheet.data_validations.dataValidation
    assert sheet.page_setup.orientation == "landscape" and "Total" in book.defined_names
    assert sheet.column_dimensions["A"].width == 20


# --- the checker -------------------------------------------------------------------------


def test_a_row_added_without_the_tables_look_is_reported(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.xlsx")

    plain = write_cells(path, [{"sheet": "Data", "at": "A5", "rows": [["Gym", 45]]}])
    matched = write_cells(
        path, [{"sheet": "Data", "at": "A6", "like_row": 4, "rows": [["Books", 30]]}]
    )

    assert any("Data!B5" in finding for finding in plain["findings"])
    assert not any("Data!B6" in finding for finding in matched["findings"])


def test_the_first_row_under_a_header_is_not_compared_with_the_header(tmp_path: Path) -> None:
    path = tmp_path / "h.xlsx"
    write_cells(path, [{"sheet": "S", "row_styles": [{"bold": True}], "rows": [["Status"]]}])

    report = write_cells(path, [{"sheet": "S", "at": "A2", "rows": [["Open"], ["Done"]]}])

    assert report["findings"] == []


def test_a_typed_number_between_formulas_is_reported(tmp_path: Path) -> None:
    report = write_cells(
        tmp_path / "p.xlsx",
        [{"sheet": "S", "rows": [[1, "=A1*2"], [2, 4], [3, "=A3*2"]]}],
    )

    assert report["findings"] == ["S!B2 is a typed number between formulas"]


def test_a_number_too_wide_for_its_column_and_a_chart_over_data_are_reported(
    tmp_path: Path,
) -> None:
    path = tmp_path / "w.xlsx"
    write_cells(path, [{"sheet": "S", "rows": [["Label", 1], ["x", 2]]}])
    modify_workbook(path, [{"op": "cols", "sheet": "S", "cols": "B", "width": 3}])

    report = write_cells(path, [{"sheet": "S", "at": "B3", "rows": [[123456789]]}])
    charted = modify_workbook(
        path, [{"op": "chart", "sheet": "S", "kind": "line", "source": "A1:B2", "at": "A1"}]
    )

    assert not any("B3 prints as ###" in f for f in report["findings"])  # widened for it
    assert any("chart covers" in f for f in charted["findings"])


# --- computed values ----------------------------------------------------------------------


def test_each_formula_written_comes_back_with_its_value(tmp_path: Path) -> None:
    path = tmp_path / "f.xlsx"

    report = write_cells(path, [{"sheet": "S", "rows": [[2, 3, "=A1*B1", "=1/0"]]}])

    assert report["formula_results"] == {"S!C1": 6, "S!D1": "#DIV/0!"}
    assert report["recalc"]["total_errors"] == 1
    with zipfile.ZipFile(path) as archive:
        assert b"<v>6</v>" in archive.read("xl/worksheets/sheet1.xml")


def test_an_edited_file_carries_its_values_and_still_recalculates_on_open(
    tmp_path: Path,
) -> None:
    path = _table(tmp_path / "t.xlsx")

    report = write_cells(path, [{"sheet": "Data", "at": "B5", "rows": [["=SUM(B2:B4)"]]}])

    assert report["formula_results"] == {"Data!B5": 1900}
    assert load_workbook(path, data_only=True)["Data"]["B5"].value == 1900
    assert load_workbook(path)["Data"]["B5"].value == "=SUM(B2:B4)"
    with zipfile.ZipFile(path) as archive:
        assert b'fullCalcOnLoad="1"' in archive.read("xl/workbook.xml")


def test_a_text_result_and_a_boolean_keep_their_types(tmp_path: Path) -> None:
    path = tmp_path / "f.xlsx"

    write_cells(path, [{"sheet": "S", "rows": [["a", '=A1&"b"', "=1>0"]]}])

    values = load_workbook(path, data_only=True)["S"]
    assert values["B1"].value == "ab" and values["C1"].value is True


# --- the tools ---------------------------------------------------------------------------


def _block_tools(root: Path) -> dict[str, Any]:
    from coscribe.tools.office.xlsx import build_spreadsheet_tools

    return {tool.__name__: tool for tool in build_spreadsheet_tools(root)}


def test_a_csv_is_copied_into_a_block_with_numbers_as_numbers(tmp_path: Path) -> None:
    (tmp_path / "data.csv").write_text("Region,Sales\nEast,1200\nWest,980.5\n", encoding="utf-8")

    report = _block_tools(tmp_path)["write_xlsx_cells"](
        path="out/book.xlsx", blocks=[{"sheet": "Data", "from_csv": "data.csv"}]
    )

    sheet = load_workbook(tmp_path / "out" / "book.xlsx")["Data"]
    assert report["path"] == "out/book.xlsx"
    assert [[c.value for c in row] for row in sheet.iter_rows()] == [
        ["Region", "Sales"],
        ["East", 1200],
        ["West", 980.5],
    ]


def test_the_tools_stay_inside_the_workspace(tmp_path: Path) -> None:
    tools = _block_tools(tmp_path / "ws")

    with pytest.raises(Exception, match="outside|not allowed|workspace"):
        tools["write_xlsx_cells"](path="../escape.xlsx", blocks=[{"sheet": "S", "rows": [[1]]}])
    with pytest.raises(Exception, match="outside|not allowed|workspace"):
        tools["write_xlsx_cells"](path="a.xlsx", blocks=[{"sheet": "S", "from_csv": "../x.csv"}])


def test_every_series_of_a_chart_gets_a_colour_so_none_is_drawn_invisibly(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.xlsx")

    modify_workbook(
        path,
        [{"op": "chart", "sheet": "Data", "kind": "line", "source": "A1:B4", "at": "E2"}],
    )

    with zipfile.ZipFile(path) as archive:
        chart = archive.read("xl/charts/chart1.xml").decode()
    assert "1F4E79" in chart


def test_reading_a_workbook_shows_its_layout(tmp_path: Path) -> None:
    from coscribe.tools.office.xlsx.toolkit import SpreadsheetToolkit

    path = _table(tmp_path / "t.xlsx")
    write_cells(path, [{"sheet": "Data", "at": "C2", "rows": [["=B2*2"]], "fill_down_to": 4}])
    modify_workbook(path, [{"op": "freeze", "sheet": "Data", "at": "A2"}])

    text = SpreadsheetToolkit(tmp_path).read_xlsx("t.xlsx")

    assert "header row 1 (bold)" in text and "frozen at A2" in text
    assert 'B2:B4 format "$"#,##0' in text
    assert "C2:C4; 3 formulas, first C2 =B2*2" in text


def test_data_labels_show_the_value_only(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.xlsx")

    modify_workbook(
        path,
        [
            {
                "op": "chart",
                "sheet": "Data",
                "kind": "column",
                "source": "A1:B4",
                "at": "E2",
                "labels": True,
            }
        ],
    )

    with zipfile.ZipFile(path) as archive:
        chart = archive.read("xl/charts/chart1.xml").decode()
    assert '<showVal val="1"/>' in chart and '<showSerName val="0"/>' in chart
    assert '<showCatName val="0"/>' in chart


def _chart_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("xl/charts/chart1.xml").decode()


def test_a_line_series_is_coloured_on_its_line_and_every_series_gets_a_colour(
    tmp_path: Path,
) -> None:
    path = tmp_path / "c.xlsx"
    header = ["Month", *[f"S{i}" for i in range(10)]]
    write_cells(path, [{"sheet": "S", "rows": [header, ["Jan", *range(10)], ["Feb", *range(10)]]}])

    modify_workbook(
        path,
        [
            {
                "op": "chart",
                "sheet": "S",
                "kind": "line",
                "source": "A1:K3",
                "at": "A6",
                "colors": ["111111"],
            }
        ],
    )

    chart = _chart_xml(path)
    assert chart.count("<a:ln") >= 10 and '<a:solidFill><a:srgbClr val="111111"' in chart
    assert chart.count("srgbClr") >= 10
    assert "1F4E79" not in chart.split("111111")[0]


def test_a_pie_takes_the_callers_colours_slice_by_slice(tmp_path: Path) -> None:
    path = _table(tmp_path / "t.xlsx")

    modify_workbook(
        path,
        [
            {
                "op": "chart",
                "sheet": "Data",
                "kind": "pie",
                "source": "A1:B4",
                "at": "E2",
                "colors": ["AA0000", "00AA00", "0000AA"],
            }
        ],
    )

    chart = _chart_xml(path)
    assert chart.count("<dPt>") == 3 and "00AA00" in chart


def test_a_csv_keeps_its_blank_lines_reads_gbk_and_never_runs_a_formula(tmp_path: Path) -> None:
    (tmp_path / "d.csv").write_bytes('区域,备注\n华东,=HYPERLINK("x")\n\n华南,1\n'.encode("gbk"))

    _block_tools(tmp_path)["write_xlsx_cells"](
        path="b.xlsx", blocks=[{"sheet": "S", "from_csv": "d.csv"}]
    )

    sheet = load_workbook(tmp_path / "b.xlsx")["S"]
    assert sheet["B2"].value == '=HYPERLINK("x")' and sheet["B2"].data_type == "s"
    assert sheet["A3"].value is None and sheet["A4"].value == "华南" and sheet["B4"].value == 1


def test_a_block_gives_rows_or_a_csv_not_both(tmp_path: Path) -> None:
    (tmp_path / "d.csv").write_text("a\n1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not both"):
        _block_tools(tmp_path)["write_xlsx_cells"](
            path="b.xlsx", blocks=[{"sheet": "S", "from_csv": "d.csv", "rows": [["a"]]}]
        )


def test_the_layout_of_a_sheet_without_values_or_with_a_theme_fill_reads(tmp_path: Path) -> None:
    from openpyxl.styles import PatternFill
    from openpyxl.styles.colors import Color

    from coscribe.tools.office.xlsx.toolkit import SpreadsheetToolkit

    book = Workbook()
    book.active["B3"].fill = PatternFill("solid", fgColor=Color(theme=4))
    book.create_sheet("T")["A1"] = "Head"
    book["T"]["A1"].fill = PatternFill("solid", fgColor=Color(theme=4))
    book.save(tmp_path / "x.xlsx")

    text = SpreadsheetToolkit(tmp_path).read_xlsx("x.xlsx")

    assert "fill theme colour 4" in text
