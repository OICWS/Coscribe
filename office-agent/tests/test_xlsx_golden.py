"""Golden (characterization) tests of the workbooks the xlsx tools write.

Each workbook is built through the public tools (`write_xlsx_cells`, `modify_xlsx`), reduced to
canonical text (`tests/xlsx_canonical.py`: every cell resolved to its value, formula and look,
then each XML part pretty-printed with sorted attributes and no build times), and compared with
a checked-in golden under `tests/golden/xlsx/`. A change in what the tools write, a style, a
cell value, a chart, a rule, shows as a diff of the golden; one that is intended edits the
golden in the same pull request, so the reviewer sees the XML that changed.
`UPDATE_GOLDENS=1 pytest tests/test_xlsx_golden.py` rewrites them; read the diff before
committing it.
"""

from __future__ import annotations

import contextlib
import difflib
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from coscribe.tools.office.xlsx import build_spreadsheet_tools

from .xlsx_canonical import canonical_parts

GOLDEN_DIR = Path(__file__).parent / "golden" / "xlsx"

Tools = dict[str, Callable[..., object]]

_STYLES = {
    "head": {"bold": True, "fill": "1F3864", "color": "FFFFFF", "align": "center"},
    "money": {"num": '"$"#,##0.00'},
    "pct": {"num": "0.0%", "italic": True},
}
_TABLE = [
    ["Region", "Revenue", "Share"],
    ["North", 1200, 0.6],
    ["South", 800.5, 0.4],
    ["Total", "=SUM(B2:B3)", "=SUM(C2:C3)"],
]


def _tools(root: Path) -> Tools:
    return {tool.__name__: tool for tool in build_spreadsheet_tools(root)}  # type: ignore[attr-defined]


def _styled_table(tools: Tools) -> None:
    tools["write_xlsx_cells"](
        path="book.xlsx",
        blocks=[
            {
                "sheet": "Sales",
                "rows": _TABLE,
                "row_styles": {"0": "head"},
                "col_styles": {"1": "money", "2": "pct"},
            }
        ],
        styles=_STYLES,
    )


def _dates_notes_and_text(tools: Tools) -> None:
    tools["write_xlsx_cells"](
        path="book.xlsx",
        blocks=[
            {
                "sheet": "Log",
                "rows": [
                    ["Date", "Code", "Hours"],
                    ["2026-01-05", {"v": "=001", "text": True}, 7.5],
                    ["2026-01-06 14:30", "A-2", {"v": 8, "note": "Includes overtime"}],
                    ["Total", None, "=SUM(C2:C3)"],
                ],
                "style": {"border": "thin"},
                "row_styles": {"0": {"bold": True, "border": {"bottom": "medium"}}},
            }
        ],
    )


def _grown_table(tools: Tools) -> None:
    _styled_table(tools)
    # Adds to a table that exists: the new row takes the look of its own columns.
    tools["write_xlsx_cells"](
        path="book.xlsx",
        blocks=[{"sheet": "Sales", "at": "A5", "rows": [["East", 300, 0.0]], "like_row": 3}],
        overwrite=True,
    )


def _fill_down(tools: Tools) -> None:
    tools["write_xlsx_cells"](
        path="book.xlsx",
        blocks=[
            {"sheet": "Calc", "rows": [["n", "double"], [1, "=A2*2"]], "fill_down_to": 5},
        ],
    )


def _from_csv(tools: Tools) -> None:
    Path("data.csv").write_text("Region,Sales\nEast,1200\nWest,980.5\n", encoding="utf-8")
    tools["write_xlsx_cells"](path="book.xlsx", blocks=[{"sheet": "Data", "from_csv": "data.csv"}])


def _cjk(tools: Tools) -> None:
    tools["write_xlsx_cells"](
        path="book.xlsx",
        blocks=[
            {
                "sheet": "季度报告",
                "rows": [["地区", "收入"], ["华北", 1200], ["华东", 980]],
                "style": {"font": "Microsoft YaHei"},
                "row_styles": {"0": {"bold": True}},
            }
        ],
    )


def _layout(tools: Tools) -> None:
    _styled_table(tools)
    tools["modify_xlsx"](
        path="book.xlsx",
        ops=[
            {"op": "cols", "sheet": "Sales", "cols": "A:C", "width": 18},
            {"op": "rows", "sheet": "Sales", "rows": "1:1", "height": 30},
            {"op": "freeze", "sheet": "Sales", "at": "A2"},
            {"op": "merge", "sheet": "Sales", "range": "A6:C6"},
            {"op": "tab_color", "sheet": "Sales", "color": "1F3864"},
            {
                "op": "print",
                "sheet": "Sales",
                "landscape": True,
                "fit_width": 1,
                "repeat_rows": "1:1",
            },
            {"op": "name", "name": "Revenue", "ref": "Sales!$B$2:$B$3"},
        ],
    )


def _sheets(tools: Tools) -> None:
    _styled_table(tools)
    tools["modify_xlsx"](
        path="book.xlsx",
        ops=[
            {"op": "add_sheet", "name": "Scratch"},
            {"op": "add_sheet", "name": "Lists", "index": 0},
            {"op": "rename_sheet", "sheet": "Scratch", "name": "Notes"},
            {"op": "add_sheet", "name": "Dropped"},
            {"op": "delete_sheet", "sheet": "Dropped"},
        ],
    )


def _chart(kind: str) -> Callable[[Tools], None]:
    def build(tools: Tools) -> None:
        _styled_table(tools)
        tools["modify_xlsx"](
            path="book.xlsx",
            ops=[
                {
                    "op": "chart",
                    "sheet": "Sales",
                    "kind": kind,
                    "source": "A1:B3",
                    "at": "E2",
                    "title": "Revenue",
                    "x_title": "Region",
                    "y_title": "USD",
                }
            ],
        )

    return build


def _rules(tools: Tools) -> None:
    tools["write_xlsx_cells"](
        path="book.xlsx",
        blocks=[
            {
                "sheet": "Tasks",
                "rows": [
                    ["Task", "Status", "Score"],
                    ["a", "Open", 3],
                    ["b", "Done", 9],
                    ["c", "Open", 6],
                ],
                "row_styles": {"0": {"bold": True}},
            }
        ],
    )
    tools["modify_xlsx"](
        path="book.xlsx",
        ops=[
            {"op": "conditional", "sheet": "Tasks", "range": "C2:C4", "rule": "color_scale"},
            {
                "op": "conditional",
                "sheet": "Tasks",
                "range": "C2:C4",
                "rule": "cell",
                "operator": "greaterThan",
                "values": [5],
                "fill": "C6EFCE",
                "color": "006100",
            },
            {
                "op": "validation",
                "sheet": "Tasks",
                "range": "B2:B4",
                "list": ["Open", "Done"],
                "message": "Pick a status",
            },
        ],
    )


WORKBOOKS: dict[str, Callable[[Tools], None]] = {
    "cjk": _cjk,
    "chart_column": _chart("column"),
    "chart_line": _chart("line"),
    "dates_notes_and_text": _dates_notes_and_text,
    "fill_down": _fill_down,
    "from_csv": _from_csv,
    "grown_table": _grown_table,
    "layout": _layout,
    "rules": _rules,
    "sheets": _sheets,
    "styled_table": _styled_table,
}


def build_workbook(name: str, root: Path) -> Path:
    """Build workbook `name` in `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    with contextlib.chdir(root):
        WORKBOOKS[name](_tools(root))
    return root / "book.xlsx"


def _render(parts: dict[str, str]) -> str:
    return "".join(f"===== {name}\n{text}" for name, text in parts.items())


@pytest.mark.parametrize("name", sorted(WORKBOOKS))
def test_workbook_matches_its_golden(name: str, tmp_path: Path) -> None:
    actual = _render(canonical_parts(build_workbook(name, tmp_path / name)))
    golden = GOLDEN_DIR / f"{name}.txt"
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
    assert actual == expected, (
        f"{golden.name} differs from what the tools build; if the change is intended, run "
        f"UPDATE_GOLDENS=1 pytest tests/test_xlsx_golden.py and commit the diff:\n{diff[:4000]}"
    )


def test_the_same_workbook_builds_to_the_same_text_twice(tmp_path: Path) -> None:
    first = _render(canonical_parts(build_workbook("chart_column", tmp_path / "a")))
    second = _render(canonical_parts(build_workbook("chart_column", tmp_path / "b")))
    assert first == second


def test_every_golden_belongs_to_a_workbook() -> None:
    stale = sorted(p.stem for p in GOLDEN_DIR.glob("*.txt") if p.stem not in WORKBOOKS)
    assert stale == [], f"goldens with no workbook that builds them: {stale}"
