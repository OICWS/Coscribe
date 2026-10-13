"""Golden (characterization) tests of the XML the xlsx tools write.

`tools/spreadsheets.py` is on the ratchet's file-size list and is to be split by pure moves.
A pure move must leave every workbook the tools write unchanged, and these tests are how that
is shown: each workbook is built through the public tools, reduced to canonical text
(`tests/pptx_canonical.py`, which also serves any Office zip) and compared with a checked-in
golden under `tests/golden/xlsx/`. A change that alters what a workbook contains edits its
golden in the same pull request, so the reviewer sees the XML that changed.
`UPDATE_GOLDENS=1 pytest tests/test_xlsx_golden.py` rewrites them; read the diff before
committing it.

`recalc_xlsx` is not covered: it runs LibreOffice, whose output is not ours to pin. The
LibreOffice pass that `write_xlsx` and `edit_xlsx_cells` run after writing a formula is
switched off for the same reason, so a formula is stored without a cached value, as openpyxl
writes it.

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

from coscribe.tools import _thumbnail, spreadsheets
from coscribe.tools.spreadsheets import build_spreadsheet_tools

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


BOOKS: dict[str, Callable[[Tools], None]] = {
    "column_widths": _column_widths,
    "frozen_panes": _frozen_panes,
    "merged_and_unmerged": _merged_and_unmerged,
    "multi_sheet_with_formulas": _multi_sheet_with_formulas,
    "plain": _plain,
}


def build_book(name: str, root: Path) -> Path:
    """Build workbook `name` in `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    BOOKS[name](_tools(root))
    return root / FILE


@pytest.fixture(autouse=True)
def _no_libreoffice(monkeypatch: pytest.MonkeyPatch) -> None:
    # The recalculation and the preview thumbnail both start LibreOffice; without it the tests
    # are fast and the same on machines with and without it.
    monkeypatch.setattr(spreadsheets, "find_soffice", lambda: None)
    monkeypatch.setattr(_thumbnail, "find_soffice", lambda: None)


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
