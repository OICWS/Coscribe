"""`write_xlsx` widens the columns of the sheet it writes to what they show, keeps a width that
was already set, and `column_widths` measures a cell the way Excel draws it."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from coscribe.tools import _thumbnail
from coscribe.tools.office.xlsx import build_spreadsheet_tools
from coscribe.tools.office.xlsx import helpers as spreadsheets
from coscribe.tools.office.xlsx.column_widths import (
    DEFAULT_WIDTH,
    MAX_WIDTH,
    displayed_text,
    fit_column_widths,
    text_width,
)
from evals.xlsx_checks import clipped_texts


@pytest.fixture(autouse=True)
def _no_libreoffice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spreadsheets, "find_soffice", lambda: None)
    monkeypatch.setattr(_thumbnail, "find_soffice", lambda: None)


def _write(root: Path, content: str, sheet_name: str = "Orders") -> None:
    tools = {tool.__name__: tool for tool in build_spreadsheet_tools(root)}  # type: ignore[attr-defined]
    tools["write_xlsx"](path="book.xlsx", content=content, sheet_name=sheet_name)


def _width(root: Path, sheet: str, letter: str) -> float:
    return load_workbook(root / "book.xlsx")[sheet].column_dimensions[letter].width


def test_a_label_wider_than_the_default_column_is_no_longer_cut_off(tmp_path: Path) -> None:
    _write(tmp_path, "| SKU | Unit price | Open tickets |\n| --- | --- | --- |\n| A1 | 3.5 | 12 |")

    book = load_workbook(tmp_path / "book.xlsx")
    assert clipped_texts(book, book) == []
    assert _width(tmp_path, "Orders", "B") >= text_width("Unit price")
    assert _width(tmp_path, "Orders", "C") >= text_width("Open tickets")


def test_a_formatted_number_wider_than_the_default_column_gets_room(tmp_path: Path) -> None:
    sheet = Workbook().active
    assert sheet is not None
    sheet.append(["区域", 12850000])
    sheet["B1"].number_format = '#,##0"元"'

    fit_column_widths(sheet, {})

    shown = displayed_text(12850000, '#,##0"元"')
    assert shown == "12,850,000元"
    # 8.43 characters hold `12850000` but not the formatted text, which prints as `###`.
    assert text_width(shown) > DEFAULT_WIDTH
    assert sheet.column_dimensions["B"].width >= text_width(shown)


@pytest.mark.parametrize(
    ("value", "number_format", "shown"),
    [
        (0.3425, "0.0%", "34.2%"),
        (-1234.5, "$#,##0;($#,##0)", "($1,234)"),
        (1285.0, '#,##0.00"万"', "1,285.00万"),
        (123456789012, "General", "123456789012"[:11]),
    ],
)
def test_a_number_is_measured_with_its_number_format(
    value: float, number_format: str, shown: str
) -> None:
    assert displayed_text(value, number_format) == shown


def test_a_cjk_character_counts_twice(tmp_path: Path) -> None:
    _write(tmp_path, "| 销售额（万元） | abcdefghijklmn | x |\n| 1 | 2 | 3 |", sheet_name="汇总")

    assert text_width("销售额（万元）") == 14
    assert _width(tmp_path, "汇总", "A") == _width(tmp_path, "汇总", "B")
    assert _width(tmp_path, "汇总", "A") >= 14


def test_one_long_note_is_capped(tmp_path: Path) -> None:
    _write(tmp_path, f"| Item | Note |\n| Desk lamp | {'very long note ' * 20} |")

    assert _width(tmp_path, "Orders", "B") == MAX_WIDTH


def test_a_title_over_empty_cells_does_not_widen_its_column(tmp_path: Path) -> None:
    _write(tmp_path, "| Quarterly sales report for all regions | | |\n| Region | Q1 | Q2 |")

    assert load_workbook(tmp_path / "book.xlsx")["Orders"].column_dimensions["A"].width in (
        None,
        13,  # openpyxl's value for a column with no width of its own
    )


def test_a_width_set_earlier_is_kept_when_the_sheet_is_written_again(tmp_path: Path) -> None:
    tools = {tool.__name__: tool for tool in build_spreadsheet_tools(tmp_path)}  # type: ignore[attr-defined]
    content = "| Product | Unit price |\n| Desk lamp | 24.5 |"
    tools["write_xlsx"](path="book.xlsx", content=content, sheet_name="Orders")
    tools["set_xlsx_column_width"](path="book.xlsx", sheet_name="Orders", columns="B", width=6)

    tools["write_xlsx"](path="book.xlsx", content=content, sheet_name="Orders")

    assert _width(tmp_path, "Orders", "B") == 6


def test_a_template_width_is_kept(tmp_path: Path) -> None:
    template = Workbook()
    sheet = template.active
    assert sheet is not None
    sheet.title = "Orders"
    sheet.column_dimensions["A"].width = 40
    sheet.column_dimensions["B"].width = 7
    template.save(tmp_path / "book.xlsx")

    _write(tmp_path, "| Product | Unit price | Open tickets |\n| Desk lamp | 24.5 | 3 |")

    assert _width(tmp_path, "Orders", "A") == 40
    assert _width(tmp_path, "Orders", "B") == 7
    assert _width(tmp_path, "Orders", "C") >= text_width("Open tickets")
