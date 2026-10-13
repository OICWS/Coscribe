"""Property tests for the lookup-formula evaluator (`XLOOKUP` / `XMATCH`).

The example tests in test_xlsx_lookup_formulas.py pick a few tables; these let
Hypothesis pick the tables, the keys and the options, and compare the evaluator
with a plain-Python reference written here from Excel's documented behaviour.
The evaluator supports only the two functions, as a whole-cell formula, with
literal or plain reference arguments (no INDEX/MATCH, and no formula printer:
the only round trip it offers is `parse_single_call`).

Generators avoid the inputs where the evaluator is known to disagree with
Excel, each tracked in an issue: a one-cell range (#156), an empty cell as the
result (#157), text with `match_mode` -1/1 (#158), and two calls joined by an
operator whose boundary arguments are both quoted strings (#159).
"""

from __future__ import annotations

import fnmatch
import shutil
import tempfile
from bisect import bisect_left, bisect_right
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from openpyxl import Workbook, load_workbook

from coscribe.tools import _xlsx_lookup_formulas as lookup

_FAST = settings(deadline=None, derandomize=True, max_examples=100)
_FILE = settings(deadline=None, derandomize=True, max_examples=25)
_LIBREOFFICE = settings(deadline=None, derandomize=True, max_examples=5)

_NUMBER = st.one_of(
    st.integers(-20, 20),
    st.integers(-80, 80).map(lambda n: n / 4),
)
_TEXT = st.text(alphabet='abcABC ",', min_size=1, max_size=4)
_SCALAR = st.one_of(_NUMBER, _TEXT, st.booleans())
_FORWARD = st.sampled_from([1, 2])
_SEARCH_MODES = st.sampled_from([1, -1, 2, -2])


# ── Plain-Python reference ──────────────────────────────────────────────────


def _kind(value: Any) -> str:
    if value is None:
        return "blank"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "num"
    return "text"


def _ref_equal(a: Any, b: Any) -> bool:
    kind = _kind(a)
    if kind != _kind(b) or kind == "blank":
        return False
    if kind == "text":
        return bool(a.casefold() == b.casefold())
    return bool(a == b)


def _pick(hits: list[int], search_mode: int) -> int | None:
    if not hits:
        return None
    return hits[0] if search_mode > 0 else hits[-1]


def _ref_exact(keys: list[Any], needle: Any, search_mode: int) -> int | None:
    return _pick([i for i, key in enumerate(keys) if _ref_equal(key, needle)], search_mode)


def _ref_approximate(
    keys: list[Any], needle: float, match_mode: int, search_mode: int
) -> int | None:
    numbers = [(i, key) for i, key in enumerate(keys) if _kind(key) == "num"]
    if match_mode == -1:
        eligible = [(i, key) for i, key in numbers if key <= needle]
        best = max((key for _, key in eligible), default=None)
    else:
        eligible = [(i, key) for i, key in numbers if key >= needle]
        best = min((key for _, key in eligible), default=None)
    return _pick([i for i, key in eligible if key == best], search_mode)


def _ref_wildcard(keys: list[Any], pattern: str, search_mode: int) -> int | None:
    hits = [
        i
        for i, key in enumerate(keys)
        if _kind(key) == "text" and fnmatch.fnmatchcase(key.casefold(), pattern.casefold())
    ]
    return _pick(hits, search_mode)


def _ref_index(keys: list[Any], needle: Any, match_mode: int, search_mode: int) -> int | None:
    if match_mode == 0:
        return _ref_exact(keys, needle, search_mode)
    if match_mode == 2:
        return _ref_wildcard(keys, needle, search_mode)
    return _ref_approximate(keys, needle, match_mode, search_mode)


def _same(actual: Any, expected: Any) -> bool:
    if isinstance(expected, str) and expected.startswith("#"):
        code = actual.code if isinstance(actual, lookup.FormulaError) else actual
        return bool(code == expected)
    if isinstance(actual, lookup.FormulaError):
        return False
    return _kind(actual) == _kind(expected) and bool(actual == expected)


# ── Generators ──────────────────────────────────────────────────────────────


@st.composite
def _lookup_case(draw: st.DrawFn) -> dict[str, Any]:
    """One XLOOKUP or XMATCH call over a generated table. Options that the
    formula text can only express in order (fallback before match mode before
    search mode) are drawn as a prefix length."""
    function = draw(st.sampled_from(["XLOOKUP", "XMATCH"]))
    match_mode = draw(st.sampled_from([0, 0, -1, 1, 2]))
    size = draw(st.integers(2, 8))
    keys = draw(st.lists(st.one_of(st.none(), _SCALAR), min_size=size, max_size=size))
    returns = draw(st.lists(_SCALAR, min_size=size, max_size=size))
    if match_mode == 2:
        needle: Any = draw(st.text(alphabet="abAB*?", min_size=1, max_size=4))
        keys = [
            draw(st.text(alphabet="abAB", min_size=1, max_size=4)) if _kind(k) != "blank" else k
            for k in keys
        ]
    elif match_mode in (-1, 1):
        needle = draw(_NUMBER)
    else:
        known = [k for k in keys if k is not None]
        needle = draw(st.one_of(st.sampled_from(known), _SCALAR) if known else _SCALAR)
    search_mode = draw(_SEARCH_MODES)
    fallback = draw(_SCALAR)
    # The formula text can only give options in order: fallback, then match
    # mode, then search mode. `given` is how many of them the text carries.
    given = draw(st.integers(0, 3 if function == "XLOOKUP" else 2))
    fallback_slots = 1 if function == "XLOOKUP" else 0
    return {
        "function": function,
        "keys": keys,
        "returns": returns,
        "needle": needle,
        "fallback": fallback if given >= fallback_slots and fallback_slots else None,
        "has_fallback": bool(fallback_slots) and given >= 1,
        "match_mode": match_mode if given >= 1 + fallback_slots else 0,
        "search_mode": search_mode if given >= 2 + fallback_slots else 1,
        "given": given,
    }


def _literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    return repr(value)


def _formula(case: dict[str, Any], keys_ref: str, returns_ref: str, prefix: str) -> str:
    args = [_literal(case["needle"]), keys_ref]
    options = [case["match_mode"], case["search_mode"]]
    if case["function"] == "XLOOKUP":
        args.append(returns_ref)
        options.insert(0, _literal(case["fallback"]) if case["has_fallback"] else None)
    args.extend(str(o) if not isinstance(o, str) else o for o in options[: case["given"]])
    return f"={prefix}{case['function']}({','.join(args)})"


def _expected(case: dict[str, Any]) -> Any:
    index = _ref_index(case["keys"], case["needle"], case["match_mode"], case["search_mode"])
    if case["function"] == "XMATCH":
        return "#N/A" if index is None else index + 1
    if index is None:
        return case["fallback"] if case["has_fallback"] else "#N/A"
    return case["returns"][index]


def _fill(sheet: Any, case: dict[str, Any], whole_column: bool = False) -> tuple[str, str]:
    for row, (key, ret) in enumerate(zip(case["keys"], case["returns"], strict=True), start=1):
        if key is not None:
            sheet.cell(row=row, column=1, value=key)
        sheet.cell(row=row, column=2, value=ret)
    if whole_column:
        return "A:A", "B:B"
    last = len(case["keys"])
    return f"A1:A{last}", f"B1:B{last}"


# ── The match index ─────────────────────────────────────────────────────────


@_FAST
@given(
    keys=st.lists(st.one_of(st.none(), _SCALAR), max_size=10),
    needle=_SCALAR,
    search_mode=_SEARCH_MODES,
)
def test_exact_match_is_the_first_or_last_equal_cell(
    keys: list[Any], needle: Any, search_mode: int
) -> None:
    expected = _ref_exact(keys, needle, search_mode)
    actual = lookup.xmatch_index(needle, keys, match_mode=0, search_mode=search_mode)
    assert (actual is lookup._NO_MATCH) == (expected is None)
    if expected is not None:
        assert actual == expected


@_FAST
@given(
    keys=st.lists(st.one_of(st.none(), _SCALAR), max_size=10),
    needle=_NUMBER,
    match_mode=st.sampled_from([-1, 1]),
    search_mode=_SEARCH_MODES,
)
def test_approximate_match_is_the_nearest_number_on_the_requested_side(
    keys: list[Any], needle: float, match_mode: int, search_mode: int
) -> None:
    expected = _ref_approximate(keys, needle, match_mode, search_mode)
    actual = lookup.xmatch_index(needle, keys, match_mode=match_mode, search_mode=search_mode)
    assert (actual is lookup._NO_MATCH) == (expected is None)
    if expected is not None:
        assert actual == expected


@_FAST
@given(
    keys=st.lists(_NUMBER, unique=True, min_size=1, max_size=10).map(sorted),
    needle=_NUMBER,
    match_mode=st.sampled_from([-1, 1]),
    search_mode=st.sampled_from([1, -1]),
)
def test_approximate_match_on_sorted_keys_agrees_with_bisect(
    keys: list[Any], needle: float, match_mode: int, search_mode: int
) -> None:
    if match_mode == -1:
        position = bisect_right(keys, needle) - 1
        expected = position if position >= 0 else None
    else:
        position = bisect_left(keys, needle)
        expected = position if position < len(keys) else None
    actual = lookup.xmatch_index(needle, keys, match_mode=match_mode, search_mode=search_mode)
    assert (actual is lookup._NO_MATCH) == (expected is None)
    if expected is not None:
        assert actual == expected


@_FAST
@given(
    keys=st.lists(st.one_of(st.none(), _NUMBER, st.text(alphabet="abAB", max_size=4)), max_size=10),
    pattern=st.text(alphabet="abAB*?", min_size=1, max_size=4),
    search_mode=_SEARCH_MODES,
)
def test_wildcard_match_agrees_with_fnmatch_on_text_cells(
    keys: list[Any], pattern: str, search_mode: int
) -> None:
    expected = _ref_wildcard(keys, pattern, search_mode)
    actual = lookup.xmatch_index(pattern, keys, match_mode=2, search_mode=search_mode)
    assert (actual is lookup._NO_MATCH) == (expected is None)
    if expected is not None:
        assert actual == expected


# ── A whole formula over a generated sheet ──────────────────────────────────


@_FAST
@given(
    case=_lookup_case(),
    prefix=st.sampled_from(["", "_xlfn.", "_XLFN."]),
    whole_column=st.booleans(),
)
def test_evaluate_formula_matches_the_reference(
    case: dict[str, Any], prefix: str, whole_column: bool
) -> None:
    workbook = Workbook()
    keys_ref, returns_ref = _fill(workbook.active, case, whole_column)

    actual = lookup.evaluate_formula(
        _formula(case, keys_ref, returns_ref, prefix), workbook.active.title, workbook
    )

    expected = _expected(case)
    assert _same(actual, expected), (actual, expected)


@_FAST
@given(
    keys=st.lists(_TEXT, unique_by=str.casefold, min_size=2, max_size=8),
    data=st.data(),
)
def test_a_whole_column_reference_reaches_the_last_row(
    keys: list[str], data: st.DataObject
) -> None:
    chosen = data.draw(st.integers(0, len(keys) - 1))
    workbook = Workbook()
    sheet = workbook.active
    for row, key in enumerate(keys, start=1):
        sheet.cell(row=row, column=1, value=key)
        sheet.cell(row=row, column=2, value=row * 10)

    whole = lookup.evaluate_formula(
        f"=XLOOKUP({_literal(keys[chosen])},A:A,B:B)", sheet.title, workbook
    )

    assert whole == (chosen + 1) * 10


@_FAST
@given(
    case=_lookup_case(),
    data=st.data(),
)
def test_a_returned_range_of_a_different_length_is_a_value_error(
    case: dict[str, Any], data: st.DataObject
) -> None:
    case = {**case, "function": "XLOOKUP"}
    extra = data.draw(st.integers(1, 3))
    workbook = Workbook()
    keys_ref, _ = _fill(workbook.active, case)
    short_ref = f"B1:B{len(case['keys']) + extra}"

    actual = lookup.evaluate_formula(
        _formula({**case, "has_fallback": False, "given": 0}, keys_ref, short_ref, ""),
        workbook.active.title,
        workbook,
    )

    assert isinstance(actual, lookup.FormulaError)
    assert actual.code == "#VALUE!"


@_FAST
@given(
    case=_lookup_case(),
    match_mode=st.integers(-5, 5).filter(lambda m: m not in (-1, 0, 1, 2)),
    search_mode=st.integers(-5, 5).filter(lambda m: m not in (-2, -1, 1, 2)),
    bad_search=st.booleans(),
)
def test_an_option_outside_the_documented_values_is_a_value_error(
    case: dict[str, Any], match_mode: int, search_mode: int, bad_search: bool
) -> None:
    workbook = Workbook()
    keys_ref, returns_ref = _fill(workbook.active, case)
    function = case["function"]
    if function == "XLOOKUP":
        args = [_literal(case["needle"]), keys_ref, returns_ref, '"x"']
    else:
        args = [_literal(case["needle"]), keys_ref]
    args += ["0", str(search_mode)] if bad_search else [str(match_mode)]

    actual = lookup.evaluate_formula(
        f"={function}({','.join(args)})", workbook.active.title, workbook
    )

    assert isinstance(actual, lookup.FormulaError)
    assert actual.code == "#VALUE!"


# ── The patched file ────────────────────────────────────────────────────────


@_FILE
@given(
    cases=st.lists(_lookup_case(), min_size=1, max_size=4),
    sheet_name=st.sampled_from(["Data", "My Sheet"]),
    prefix=st.sampled_from(["", "_xlfn."]),
    whole_column=st.booleans(),
)
def test_patched_cells_read_back_as_the_reference_values(
    cases: list[dict[str, Any]], sheet_name: str, prefix: str, whole_column: bool
) -> None:
    folder = Path(tempfile.mkdtemp(prefix="coscribe_lookup_prop_"))
    try:
        workbook = Workbook()
        out = workbook.active
        out.title = "Out"
        data = workbook.create_sheet(sheet_name)
        qualified = f"'{sheet_name}'!" if " " in sheet_name else f"{sheet_name}!"
        # Each case gets its own pair of columns, so a patch that lands on the
        # wrong sheet or reads the wrong columns shows up as a wrong value.
        for number, case in enumerate(cases, start=1):
            key_column, return_column = 2 * number - 1, 2 * number
            for row, (key, ret) in enumerate(zip(case["keys"], case["returns"], strict=True), 1):
                if key is not None:
                    data.cell(row=row, column=key_column, value=key)
                data.cell(row=row, column=return_column, value=ret)
            letters = [
                data.cell(row=1, column=c).column_letter for c in (key_column, return_column)
            ]
            last = len(case["keys"])
            spans = [f"{c}:{c}" if whole_column else f"{c}1:{c}{last}" for c in letters]
            out.cell(
                row=number,
                column=1,
                value=_formula(case, qualified + spans[0], qualified + spans[1], prefix),
            )
        path = folder / "lookups.xlsx"
        workbook.save(str(path))

        report = lookup.evaluate_and_patch_lookup_formulas(path)

        assert report["formulas_evaluated"] == len(cases)
        reopened = load_workbook(str(path), data_only=True)
        for number, case in enumerate(cases, start=1):
            cell = reopened["Out"].cell(row=number, column=1)
            expected = _expected(case)
            assert _same(cell.value, expected), (number, cell.value, expected)
            if isinstance(expected, str) and expected.startswith("#"):
                assert cell.data_type == "e"
            elif _kind(expected) == "bool":
                assert cell.data_type == "b"
            elif _kind(expected) == "num":
                assert cell.data_type == "n"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


# ── Parsing ─────────────────────────────────────────────────────────────────

_REFERENCES = st.sampled_from(
    ["A1", "$A$1:$B$9", "A:A", "2:2", "'My Sheet'!B:B", "Data!C3:C9", "Sheet2!$D$4"]
)
_STRING_LITERALS = st.text(alphabet='ab ,()"+', max_size=6).map(
    lambda s: '"' + s.replace('"', '""') + '"'
)
_SIMPLE_ARGS = st.one_of(
    _REFERENCES, _STRING_LITERALS, _NUMBER.map(repr), st.sampled_from(["TRUE", "FALSE"])
)
_NESTED_CALLS = st.builds(
    lambda name, inner: f"{name}({','.join(inner)})",
    st.sampled_from(["IF", "SUM", "INDEX"]),
    st.lists(_SIMPLE_ARGS, min_size=1, max_size=3),
)
_ARGS = st.one_of(_SIMPLE_ARGS, _NESTED_CALLS)
_CALL_NAMES = st.sampled_from(["XLOOKUP", "xlookup", "XLookup", "XMATCH", "xmatch"])
_PREFIXES = st.sampled_from(["", "_xlfn.", "_XLFN.", "_xlfn._xlws.", "_XLFN._XLWS."])


@_FAST
@given(
    name=_CALL_NAMES,
    prefix=_PREFIXES,
    args=st.lists(_ARGS, min_size=1, max_size=6),
    padding=st.lists(st.sampled_from(["", " ", "  "]), min_size=12, max_size=12),
)
def test_parse_single_call_returns_the_name_and_the_arguments_that_were_joined(
    name: str, prefix: str, args: list[str], padding: list[str]
) -> None:
    padded = [f"{padding[2 * i]}{arg}{padding[2 * i + 1]}" for i, arg in enumerate(args)]

    parsed = lookup.parse_single_call(f"={prefix}{name}({','.join(padded)})")

    assert parsed == (name.upper(), args)


@_FAST
@given(
    name=st.sampled_from(
        ["SUM", "INDEX", "MATCH", "XLOOKUPS", "MYXLOOKUP", "XLOOKUP.X", "VLOOKUP"]
    ),
    prefix=_PREFIXES,
    args=st.lists(_SIMPLE_ARGS, min_size=1, max_size=4),
)
def test_parse_single_call_declines_other_functions(
    name: str, prefix: str, args: list[str]
) -> None:
    assert lookup.parse_single_call(f"={prefix}{name}({','.join(args)})") is None


@_FAST
@given(
    first=st.tuples(_CALL_NAMES, st.lists(_SIMPLE_ARGS, min_size=2, max_size=3)),
    second=st.tuples(_CALL_NAMES, st.lists(_SIMPLE_ARGS, min_size=2, max_size=3)),
    operator=st.sampled_from(["+", "-", "*", "/", "&", "=", ">", "<>"]),
    shape=st.sampled_from(["call-op-call", "call-op-number", "number-op-call"]),
)
def test_a_formula_that_is_not_one_call_is_declined(
    first: tuple[str, list[str]],
    second: tuple[str, list[str]],
    operator: str,
    shape: str,
) -> None:
    # Only the first call's last argument is kept clear of string literals:
    # a quoted last argument followed by a quoted first argument of the
    # second call reads as one string spanning the `)op f(` between them.
    first_name, first_args = first
    first_args = [*first_args[:-1], "A1"]
    one = f"{first_name}({','.join(first_args)})"
    other = f"{second[0]}({','.join(second[1])})"
    text = {
        "call-op-call": f"={one}{operator}{other}",
        "call-op-number": f"={one}{operator}1",
        "number-op-call": f"=1{operator}{other}",
    }[shape]
    workbook = Workbook()

    assert lookup.evaluate_formula(text, workbook.active.title, workbook) is lookup._UNRESOLVABLE


# ── LibreOffice ─────────────────────────────────────────────────────────────


def _recalculate(path: Path) -> dict[str, object]:
    from coscribe.tools import spreadsheets

    return spreadsheets._recalc_xlsx_and_evaluate_lookups(path)


def _libreoffice_actually_works() -> bool:
    folder = Path(tempfile.mkdtemp(prefix="coscribe_lookup_lo_probe_"))
    try:
        workbook = Workbook()
        workbook.active["A1"] = "=1+1"
        workbook.save(str(folder / "probe.xlsx"))
        return _recalculate(folder / "probe.xlsx")["status"] != "skipped"
    finally:
        shutil.rmtree(folder, ignore_errors=True)


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
@_LIBREOFFICE
@given(
    numbers=st.lists(st.integers(-30, 30), unique=True, min_size=2, max_size=8).map(sorted),
    texts=st.lists(st.text(alphabet="abAB", min_size=1, max_size=3), min_size=2, max_size=6),
    needles=st.lists(st.integers(-35, 35), min_size=3, max_size=3),
    text_needles=st.lists(st.text(alphabet="abAB", min_size=1, max_size=3), min_size=2, max_size=2),
    pattern=st.text(alphabet="ab*?", min_size=1, max_size=3),
)
def test_evaluator_agrees_with_libreoffice_on_the_equivalent_match_formulas(
    numbers: list[int],
    texts: list[str],
    needles: list[int],
    text_needles: list[str],
    pattern: str,
) -> None:
    """LibreOffice before 24.8 cannot evaluate XLOOKUP/XMATCH at all, so each
    call is paired with the INDEX/MATCH formula LibreOffice does compute, and
    the two cells must hold the same value after one recalculation."""
    folder = Path(tempfile.mkdtemp(prefix="coscribe_lookup_lo_"))
    try:
        workbook = Workbook()
        data = workbook.active
        data.title = "Data"
        descending = list(reversed(numbers))
        for row, number in enumerate(numbers, start=1):
            data.cell(row=row, column=1, value=number)
            data.cell(row=row, column=2, value=f"r{number}")
            data.cell(row=row, column=4, value=descending[row - 1])
        for row, text in enumerate(texts, start=1):
            data.cell(row=row, column=3, value=text)
            data.cell(row=row, column=5, value=row * 10)
        numbers_ref = f"Data!$A$1:$A${len(numbers)}"
        returns_ref = f"Data!$B$1:$B${len(numbers)}"
        descending_ref = f"Data!$D$1:$D${len(numbers)}"
        texts_ref = f"Data!$C$1:$C${len(texts)}"
        text_returns_ref = f"Data!$E$1:$E${len(texts)}"

        pairs: list[tuple[str, str]] = [
            (
                f'=_xlfn.XLOOKUP({needles[0]},{numbers_ref},{returns_ref},"none")',
                f'=_xlfn.IFNA(INDEX({returns_ref},MATCH({needles[0]},{numbers_ref},0)),"none")',
            ),
            (
                f"=_xlfn.XMATCH({needles[1]},{numbers_ref})",
                f"=MATCH({needles[1]},{numbers_ref},0)",
            ),
            (
                f"=_xlfn.XMATCH({needles[2]},{numbers_ref},-1)",
                f"=MATCH({needles[2]},{numbers_ref},1)",
            ),
            (
                f"=_xlfn.XMATCH({needles[2]},{descending_ref},1)",
                f"=MATCH({needles[2]},{descending_ref},-1)",
            ),
        ]
        for needle in text_needles:
            pairs.append(
                (
                    f'=_xlfn.XLOOKUP("{needle}",{texts_ref},{text_returns_ref},"none")',
                    f'=_xlfn.IFNA(INDEX({text_returns_ref},MATCH("{needle}",{texts_ref},0)),"none")',
                )
            )
        pairs.append(
            (
                f'=_xlfn.XMATCH("{pattern}",{texts_ref},2)',
                f'=MATCH("{pattern}",{texts_ref},0)',
            )
        )
        out = workbook.create_sheet("Out")
        for row, (native, reference) in enumerate(pairs, start=1):
            out.cell(row=row, column=1, value=native)
            out.cell(row=row, column=2, value=reference)
        path = folder / "lookups.xlsx"
        workbook.save(str(path))

        assert _recalculate(path)["status"] != "skipped"

        values = load_workbook(str(path), data_only=True)["Out"]
        for row, (native, reference) in enumerate(pairs, start=1):
            ours = values.cell(row=row, column=1).value
            theirs = values.cell(row=row, column=2).value
            assert ours == theirs, (native, reference, ours, theirs)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
