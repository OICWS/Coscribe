"""Golden (characterization) tests of the XML the xlsx tools write.

`tools/spreadsheets.py` is on the ratchet's file-size list and is to be split by pure moves.
A pure move must leave every workbook the tools write unchanged, and these tests are how that
is shown: each workbook is built through the public tools, reduced to canonical text
(`tests/pptx_canonical.py`, which also serves any Office zip) and compared with a checked-in
golden under `tests/golden/xlsx/`. A change that alters what a workbook contains edits its
golden in the same pull request, so the reviewer sees the XML that changed.
`UPDATE_GOLDENS=1 pytest tests/test_xlsx_golden.py` rewrites them; read the diff before
committing it.

A formula is stored with the value the in-process engine computed for it (`calc.py`), the
same on every machine, so the goldens pin it too.

The only value blanked is the creation and modification time in `docProps/core.xml` (see
`pptx_canonical.py`); the workbook tools write no other time or random id.
"""

from __future__ import annotations

import difflib
import os
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from coscribe.tools.office.xlsx import build_spreadsheet_tools

from .pptx_canonical import canonical_parts

GOLDEN_DIR = Path(__file__).parent / "golden" / "xlsx"
FILE = "book.xlsx"

Tools = dict[str, Callable[..., object]]


def _tools(root: Path) -> Tools:
    return {tool.__name__: tool for tool in build_spreadsheet_tools(root)}  # type: ignore[attr-defined]


_SALES = (
    "| Region | Q1 | Q2 | Note |\n| --- | --- | --- | --- |\n"
    "| North | 120 | 135.5 | on plan |\n| South | 80 | 95 | late start |\n"
    "| West | 60 | 70.25 | new |"
)


def _plain(tools: Tools) -> None:
    tools["write_xlsx"](path=FILE, content=_SALES, sheet_name="Sales")


def _multi_sheet_with_formulas(tools: Tools) -> None:
    tools["write_xlsx"](path=FILE, content=_SALES, sheet_name="Sales")
    tools["write_xlsx"](
        path=FILE,
        content="| Region | Manager | Start date |\n| --- | --- | --- |\n"
        "| North | Ana | 2026-01-15 |\n| South | Ben | 2026-03-01 |\n| West | Chen | 2026-06-30 |",
        sheet_name="Managers",
    )
    tools["write_xlsx"](
        path=FILE,
        content="| Item | Value |\n| --- | --- |\n| Total Q1 | =SUM(Sales!B2:B4) |\n"
        "| Growth | =(SUM(Sales!C2:C4)-SUM(Sales!B2:B4))/SUM(Sales!B2:B4) |\n"
        '| South manager | =INDEX(Managers!B2:B4,MATCH("South",Managers!A2:A4,0)) |',
        sheet_name="Summary",
    )


def _column_widths(tools: Tools) -> None:
    _plain(tools)
    tools["set_xlsx_column_width"](path=FILE, sheet_name="Sales", columns="A", width=18)
    tools["set_xlsx_column_width"](path=FILE, sheet_name="Sales", columns="B:C", width=9.5)
    tools["set_xlsx_column_width"](path=FILE, sheet_name="Sales", columns="D", width=32)


def _frozen_panes(tools: Tools) -> None:
    _multi_sheet_with_formulas(tools)
    tools["freeze_xlsx_panes"](path=FILE, sheet_name="Sales", cell="B2")
    tools["freeze_xlsx_panes"](path=FILE, sheet_name="Managers", cell="A2")
    tools["freeze_xlsx_panes"](path=FILE, sheet_name="Summary", cell="C1")


def _merged_and_unmerged(tools: Tools) -> None:
    tools["write_xlsx"](
        path=FILE,
        content="| Quarterly report | | | |\n| Region | Q1 | Q2 | Q3 |\n| North | 1 | 2 | 3 |\n"
        "| South | 4 | 5 | 6 |\n| Footnote | | | |",
        sheet_name="Report",
    )
    tools["merge_xlsx_cells"](path=FILE, sheet_name="Report", cell_range="A1:D1")
    tools["merge_xlsx_cells"](path=FILE, sheet_name="Report", cell_range="B5:D5")
    tools["merge_xlsx_cells"](path=FILE, sheet_name="Report", cell_range="A3:A4")
    tools["unmerge_xlsx_cells"](path=FILE, sheet_name="Report", cell_range="A3:A4")


def _number_formats_and_fonts(tools: Tools) -> None:
    tools["write_xlsx"](
        path=FILE,
        content="| Item | Price | Margin | Delta |\n| --- | --- | --- | --- |\n"
        "| Widget | 1250 | 0.15 | -300 |\n| Gadget | 980.5 | 0.075 | 0 |\n"
        "| Total | =SUM(B2:B3) | =AVERAGE(C2:C3) | =SUM(D2:D3) |",
        sheet_name="Pricing",
    )
    tools["format_xlsx_cells"](
        path=FILE, sheet_name="Pricing", cell_range="A1:D1", bold=True, font_color="1F4E79"
    )
    tools["format_xlsx_cells"](
        path=FILE, sheet_name="Pricing", cell_range="B2:B4", number_format="$#,##0"
    )
    tools["format_xlsx_cells"](
        path=FILE,
        sheet_name="Pricing",
        cell_range="C2:C4",
        number_format="0.0%",
        font_color="0000FF",
    )
    tools["format_xlsx_cells"](
        path=FILE,
        sheet_name="Pricing",
        cell_range="D2:D4",
        number_format="$#,##0;($#,##0);-",
        font_color="FF0000",
        bold=True,
    )


_SCORES = (
    "| Name | Score | Hours |\n| --- | --- | --- |\n| Ana | 91 | 12 |\n| Ben | 47 | 30 |\n"
    "| Chen | 68 | 18 |\n| Dara | 83 | 22 |"
)


def _conditional_formats(tools: Tools) -> None:
    tools["write_xlsx"](path=FILE, content=_SCORES, sheet_name="Scores")
    tools["add_xlsx_conditional_format"](
        path=FILE,
        sheet_name="Scores",
        cell_range="B2:B5",
        rule_type="cell_is",
        operator="<",
        formula="50",
        fill_color="FFC7CE",
    )
    tools["add_xlsx_conditional_format"](
        path=FILE,
        sheet_name="Scores",
        cell_range="B2:B5",
        rule_type="cell_is",
        operator="between",
        formula="80,100",
        fill_color="C6EFCE",
    )
    tools["add_xlsx_conditional_format"](
        path=FILE,
        sheet_name="Scores",
        cell_range="C2:C5",
        rule_type="color_scale",
        min_color="FFFFFF",
        mid_color="FFEB84",
        max_color="F8696B",
    )
    tools["add_xlsx_conditional_format"](
        path=FILE,
        sheet_name="Scores",
        cell_range="B2:B5",
        rule_type="data_bar",
        fill_color="638EC6",
    )


def _data_validation(tools: Tools) -> None:
    tools["write_xlsx"](
        path=FILE,
        content="| Task | Status | Priority | Hours |\n| --- | --- | --- | --- |\n"
        "| Draft | Open | 1 | 4.5 |\n| Review | Done | 3 | 2 |",
        sheet_name="Tasks",
    )
    tools["write_xlsx"](
        path=FILE,
        content="| Status |\n| --- |\n| Open |\n| Done |\n| Blocked |",
        sheet_name="Lists",
    )
    tools["set_xlsx_data_validation"](
        path=FILE,
        sheet_name="Tasks",
        cell_range="B2:B20",
        validation_type="list",
        formula1="Open,Done,Blocked",
        error_message="Pick a status from the list",
        error_title="Invalid status",
    )
    tools["set_xlsx_data_validation"](
        path=FILE,
        sheet_name="Tasks",
        cell_range="C2:C20",
        validation_type="whole",
        formula1="1",
        formula2="5",
        error_message="Priority is 1 to 5",
    )
    tools["set_xlsx_data_validation"](
        path=FILE,
        sheet_name="Tasks",
        cell_range="D2:D20",
        validation_type="decimal",
        operator="greaterThanOrEqual",
        formula1="0",
        allow_blank=False,
    )
    tools["set_xlsx_data_validation"](
        path=FILE,
        sheet_name="Tasks",
        cell_range="B21:B30",
        validation_type="list",
        formula1="Lists!$A$2:$A$4",
    )


def _chart(chart_type: str, content: str, **kwargs: str) -> Callable[[Tools], None]:
    def build(tools: Tools) -> None:
        tools["write_xlsx"](path=FILE, content=content, sheet_name="Data")
        tools["add_xlsx_chart"](
            path=FILE, sheet_name="Data", chart_type=chart_type, title="Results", **kwargs
        )

    return build


_ONE_SERIES = "| Quarter | Revenue |\n| --- | --- |\n| Q1 | 100 |\n| Q2 | 120 |\n| Q3 | 90 |"
_THREE_SERIES = (
    "| Quarter | North | South | West |\n| --- | --- | --- | --- |\n"
    "| Q1 | 10 | 8 | 5 |\n| Q2 | 12 | 9 | 7 |\n| Q3 | 9 | 11 | 6 |"
)


def _edit_cells_keeps_structure(tools: Tools) -> None:
    _merged_and_unmerged(tools)
    tools["format_xlsx_cells"](
        path=FILE, sheet_name="Report", cell_range="B3:D4", number_format="0.00", bold=True
    )
    tools["freeze_xlsx_panes"](path=FILE, sheet_name="Report", cell="A3")
    tools["edit_xlsx_cells"](
        path=FILE, sheet_name="Report", start_cell="B3", content="| 10 | 20 |\n| 40 | =B4*2 |"
    )
    tools["edit_xlsx_cells"](
        path=FILE, sheet_name="Report", start_cell="A1", content="| Q4 report |"
    )


BOOKS: dict[str, Callable[[Tools], None]] = {
    "chart_bar": _chart("bar", _ONE_SERIES),
    "chart_line_three_series": _chart("line", _THREE_SERIES, anchor="G2"),
    "chart_pie_subset": _chart("pie", _THREE_SERIES, data_range="A1:B4"),
    "column_widths": _column_widths,
    "conditional_formats": _conditional_formats,
    "data_validation": _data_validation,
    "edit_cells_keeps_structure": _edit_cells_keeps_structure,
    "frozen_panes": _frozen_panes,
    "merged_and_unmerged": _merged_and_unmerged,
    "multi_sheet_with_formulas": _multi_sheet_with_formulas,
    "number_formats_and_fonts": _number_formats_and_fonts,
    "plain": _plain,
}


def build_book(name: str, root: Path) -> Path:
    """Build workbook `name` in `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    BOOKS[name](_tools(root))
    return root / FILE


# The theme, the content types and the package relationships are the same in every workbook.
# `xl/styles.xml` is not listed: any workbook that formats a cell writes its own.
SHARED_GOLDEN = GOLDEN_DIR / "_shared.txt"
_SHARED_PREFIXES = ("xl/theme/", "_rels/", "docProps/app.xml")
_SHARED_SOURCE_BOOK = "plain"


def _shared_parts(parts: dict[str, str]) -> dict[str, str]:
    return {name: text for name, text in parts.items() if name.startswith(_SHARED_PREFIXES)}


def _render(parts: dict[str, str]) -> str:
    return "".join(f"===== {name}\n{text}" for name, text in parts.items())


def _parse(text: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for chunk in re.split(r"^===== ", text, flags=re.MULTILINE)[1:]:
        name, _, body = chunk.partition("\n")
        parts[name] = body
    return parts


def _book_golden_text(parts: dict[str, str], shared: dict[str, str]) -> str:
    return _render(
        {
            name: "<same as _shared.txt>\n" if shared.get(name) == text else text
            for name, text in parts.items()
        }
    )


def _expected_and_diff(golden: Path, actual: str) -> tuple[str, str]:
    if os.environ.get("UPDATE_GOLDENS") == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(actual, encoding="utf-8", newline="\n")
    expected = golden.read_text(encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            f"golden/xlsx/{golden.name}",
            "built now",
            n=2,
        )
    )
    return expected, (
        f"{golden.name} differs from what the tools build; if the change is intended, run "
        f"UPDATE_GOLDENS=1 pytest tests/test_xlsx_golden.py and commit the diff:\n{diff[:4000]}"
    )


def _built_shared(tmp_path: Path) -> dict[str, str]:
    book = build_book(_SHARED_SOURCE_BOOK, tmp_path / "_shared")
    return _shared_parts(canonical_parts(book))


def test_shared_golden_matches_the_plain_workbook(tmp_path: Path) -> None:
    actual = _render(_built_shared(tmp_path))
    expected, message = _expected_and_diff(SHARED_GOLDEN, actual)
    assert actual == expected, message


@pytest.mark.parametrize("name", sorted(BOOKS))
def test_workbook_matches_its_golden(name: str, tmp_path: Path) -> None:
    parts = canonical_parts(build_book(name, tmp_path / name))
    # When regenerating, the shared golden may not be written yet (test order is not fixed).
    shared = (
        _built_shared(tmp_path)
        if os.environ.get("UPDATE_GOLDENS") == "1"
        else _parse(SHARED_GOLDEN.read_text(encoding="utf-8"))
    )
    actual = _book_golden_text(parts, shared)
    expected, message = _expected_and_diff(GOLDEN_DIR / f"{name}.txt", actual)
    assert actual == expected, message


def test_the_shared_golden_round_trips_through_the_parser() -> None:
    text = SHARED_GOLDEN.read_text(encoding="utf-8")
    assert _render(_parse(text)) == text


def test_every_golden_belongs_to_a_workbook() -> None:
    stale = sorted(
        path.stem
        for path in GOLDEN_DIR.glob("*.txt")
        if path.stem not in BOOKS and path != SHARED_GOLDEN
    )
    assert stale == [], f"goldens with no workbook that builds them: {stale}"
