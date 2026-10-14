"""`write_xlsx` widens the columns of the sheet it writes to what they show, keeps a width that
was already set, and `column_widths` measures a cell the way Excel draws it."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from coscribe.tools import _thumbnail
from coscribe.tools.office.xlsx import build_spreadsheet_tools
from coscribe.tools.office.xlsx.column_layout import fit_columns
from coscribe.tools.office.xlsx.column_widths import MAX_WIDTH, displayed_text, text_width
from evals.xlsx_checks import clipped_texts

FILE = "book.xlsx"


@pytest.fixture(autouse=True)
def _no_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_thumbnail, "find_soffice", lambda: None)


def _tools(root: Path) -> dict[str, object]:
    return {tool.__name__: tool for tool in build_spreadsheet_tools(root)}  # type: ignore[attr-defined]


def _write(root: Path, content: str, sheet_name: str = "Orders") -> None:
    _tools(root)["write_xlsx"](path=FILE, content=content, sheet_name=sheet_name)  # type: ignore[operator]


def _width(root: Path, letter: str, sheet: str = "Orders") -> float:
    return load_workbook(root / FILE)[sheet].column_dimensions[letter].width


def _cols(root: Path) -> list[dict[str, str]]:
    """The `<col>` elements of the first sheet as the file has them."""
    with zipfile.ZipFile(root / FILE) as archive:
        xml = archive.read("xl/worksheets/sheet1.xml").decode()
    return [dict(re.findall(r'(\w+)="([^"]*)"', col)) for col in re.findall(r"<col [^>]*>", xml)]


def _book_with_cols(root: Path, cols: str) -> None:
    """A sheet Orders whose `<cols>` is exactly `cols`, as a person's file can have it and
    openpyxl cannot write it."""
    book = Workbook()
    assert book.active is not None
    book.active.title = "Orders"
    book.save(root / FILE)
    with zipfile.ZipFile(root / FILE) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
    with zipfile.ZipFile(root / FILE, "w") as archive:
        for info, data in entries:
            if info.filename == "xl/worksheets/sheet1.xml":
                data = data.replace(b"<sheetData", f"<cols>{cols}</cols><sheetData".encode())
            archive.writestr(info, data)


def test_a_label_wider_than_the_default_column_is_no_longer_cut_off(tmp_path: Path) -> None:
    _write(tmp_path, "| SKU | Unit price | Open tickets |\n| --- | --- | --- |\n| A1 | 3.5 | 12 |")

    book = load_workbook(tmp_path / FILE)
    assert clipped_texts(book, book) == []
    assert _width(tmp_path, "C") >= text_width("Open tickets")


def test_a_formatted_number_wider_than_the_default_column_gets_room() -> None:
    sheet = Workbook().active
    assert sheet is not None
    sheet.append(["区域", 12850000])
    sheet["B1"].number_format = '#,##0"元"'

    fit_columns(sheet, [])

    # 8.43 characters hold `12850000` but not `12,850,000元`, which prints as `###`.
    assert sheet.column_dimensions["B"].width >= text_width("12,850,000元")


@pytest.mark.parametrize(
    ("value", "fmt", "shown"),
    [
        (12850000, '#,##0"元"', "12,850,000元"),
        (0.3425, "0.0%", "34.2%"),
        (-1234.5, "$#,##0;($#,##0)", "($1,234)"),
        (1285.0, '#,##0.00"万"', "1,285.00万"),
        (123456789012, "General", "12345678901"),
        (12345678, "0.00E+00", "1.23E+07"),
        (1234567, '#,##0,"K"', "1,235K"),
        (-5, '0" a;b";(0)', "(5)"),
        (5, '0" a;b";(0)', "5 a;b"),
        (-5, "0\\;;(0)", "(5)"),
    ],
)
def test_a_number_is_measured_with_its_number_format(value: float, fmt: str, shown: str) -> None:
    assert displayed_text(value, fmt) == shown


def test_a_format_that_is_not_rendered_is_measured_by_its_own_length() -> None:
    assert text_width(displayed_text(0.5, "# ??/??")) >= len("# ??/??")
    assert text_width(displayed_text(46000, "yyyy-mm-dd")) >= len("2025-12-10")


def test_a_cjk_character_counts_twice_and_one_long_note_is_capped(tmp_path: Path) -> None:
    _write(tmp_path, f"| 销售额（万元） | abcdefghijklmn | {'long note ' * 20} |\n| 1 | 2 | 3 |")

    assert text_width("销售额（万元）") == 14
    assert _width(tmp_path, "A") == _width(tmp_path, "B") >= 14
    assert _width(tmp_path, "C") == MAX_WIDTH


def test_a_title_widens_its_column_only_past_the_empty_cells_beside_it(tmp_path: Path) -> None:
    _write(tmp_path, "| Quarterly sales report | | |\n| Region | Q1 | Q2 |")
    assert _cols(tmp_path) == []

    title = "Quarterly sales report for all regions"
    _write(tmp_path, f"| {title} | | |\n| Region | Q1 | Q2 |")
    assert _width(tmp_path, "A") >= text_width(title)


def test_writing_a_sheet_again_widens_a_column_but_never_narrows_it(tmp_path: Path) -> None:
    _write(tmp_path, "| Item | Price |\n| Lamp | 1 |")
    assert _cols(tmp_path) == []

    _write(tmp_path, "| Item | Price |\n| Lamp | 123456789.5 |")
    wide = _width(tmp_path, "B")
    assert wide >= len("123456789.5")

    _write(tmp_path, "| Item | Price |\n| Lamp | 1 |")
    assert _width(tmp_path, "B") == wide


def test_a_width_set_earlier_is_kept_unless_the_content_needs_more(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    content = "| Product | Unit price |\n| Desk lamp | 24.5 |"
    tools["write_xlsx"](path=FILE, content=content, sheet_name="Orders")  # type: ignore[operator]
    tools["set_xlsx_column_width"](path=FILE, sheet_name="Orders", columns="A:B", width=30)  # type: ignore[operator]
    tools["write_xlsx"](path=FILE, content=content, sheet_name="Orders")  # type: ignore[operator]
    assert _width(tmp_path, "A") == _width(tmp_path, "B") == 30

    tools["set_xlsx_column_width"](path=FILE, sheet_name="Orders", columns="B", width=6)  # type: ignore[operator]
    tools["write_xlsx"](path=FILE, content=content, sheet_name="Orders")  # type: ignore[operator]
    assert 6 < _width(tmp_path, "B") and _width(tmp_path, "B") >= text_width("Unit price")


def test_a_template_range_keeps_its_width_where_the_content_fits(tmp_path: Path) -> None:
    _book_with_cols(
        tmp_path, '<col min="1" max="1" width="40"/><col min="2" max="16384" width="7"/>'
    )

    _write(tmp_path, "| Product | Unit price | x |\n| Desk lamp | 24.5 | 3 |")

    assert [(c["min"], c["max"], c["width"]) for c in _cols(tmp_path)] == [
        ("1", "1", "40"),
        ("2", "2", "12"),
        ("3", "16384", "7"),
    ]


def test_a_template_column_keeps_its_look_and_a_hidden_or_closed_one_stays_so(
    tmp_path: Path,
) -> None:
    _book_with_cols(
        tmp_path,
        '<col min="1" max="1" hidden="1"/><col min="2" max="2" width="0" customWidth="1"/>'
        '<col min="3" max="16384" outlineLevel="1"/>',
    )

    _write(tmp_path, "| Product | Unit price | Open tickets |\n| Desk lamp | 24.5 | 3 |")

    hidden, closed, sized, rest = _cols(tmp_path)
    assert hidden["hidden"] == "1" and "width" not in hidden
    assert closed["width"] == "0"
    assert sized["outlineLevel"] == "1" and float(sized["width"]) >= text_width("Open tickets")
    assert (rest["min"], rest["max"], rest["outlineLevel"]) == ("4", "16384", "1")
    assert "width" not in rest


def test_a_number_format_applied_later_widens_its_column(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    _write(tmp_path, "| 区域 | 销售额 | 备注 |\n| 华东 | 12850000 | x |\n| 华北 | 9420000 | x |")
    assert _width(tmp_path, "B") < text_width("12,850,000元")

    tools["format_xlsx_cells"](  # type: ignore[operator]
        path=FILE, sheet_name="Orders", cell_range="B2:B3", number_format='#,##0"元"'
    )
    assert _width(tmp_path, "B") >= text_width("12,850,000元")

    tools["set_xlsx_column_width"](path=FILE, sheet_name="Orders", columns="B", width=30)  # type: ignore[operator]
    tools["format_xlsx_cells"](  # type: ignore[operator]
        path=FILE, sheet_name="Orders", cell_range="B2:B3", number_format="0"
    )
    assert _width(tmp_path, "B") == 30


def test_edit_xlsx_cells_widens_the_columns_it_wrote(tmp_path: Path) -> None:
    _book_with_cols(
        tmp_path,
        '<col min="1" max="3" width="14" customWidth="1"/><col min="7" max="7" hidden="1"/>',
    )

    _tools(tmp_path)["edit_xlsx_cells"](  # type: ignore[operator]
        path=FILE,
        sheet_name="Orders",
        start_cell="D1",
        content="| Product | Unit price | Line total | Notes |\n| Desk lamp | 24.9 | =E2*2 | x |",
    )

    cols = [(c["min"], c["max"], c.get("width"), c.get("hidden")) for c in _cols(tmp_path)]
    assert cols == [
        ("1", "3", "14", None),
        ("4", "4", "11", None),
        ("5", "5", "12", None),
        ("6", "6", "12", None),
        ("7", "7", None, "1"),
    ]


def test_edit_xlsx_cells_leaves_merged_text_and_text_with_room_beside_it(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    _write(tmp_path, "| a | b | c |\n| 1 | 2 | 3 |")
    tools["merge_xlsx_cells"](path=FILE, sheet_name="Orders", cell_range="A3:C3")  # type: ignore[operator]

    tools["edit_xlsx_cells"](  # type: ignore[operator]
        path=FILE,
        sheet_name="Orders",
        start_cell="A3",
        content="| 123456789012 |\n| Open orders: see below |",
    )

    assert _cols(tmp_path) == []
