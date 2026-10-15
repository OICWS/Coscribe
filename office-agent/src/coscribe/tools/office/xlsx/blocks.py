"""The operations that write a workbook, in a form no engine owns: openpyxl executes them now,
Excel (COM) and an Office.js add-in can later (decision 0011). Parsing validates everything
before any engine touches a file, so a bad call changes nothing."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from typing import Any

from .helpers import _validate_and_normalize_formula

_HEX = re.compile(r"#?[0-9A-Fa-f]{6}")
_CELL = re.compile(r"\$?([A-Za-z]{1,3})\$?([1-9][0-9]{0,6})")
_BORDER_STYLES = frozenset({"thin", "medium", "thick", "double", "dashed", "dotted", "none"})
_SIDES = ("top", "bottom", "left", "right")
_CHOICES: dict[str, frozenset[str]] = {
    "align": frozenset({"left", "center", "right"}),
    "valign": frozenset({"top", "center", "bottom"}),
}
_FLAGS = ("bold", "italic", "underline", "wrap")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?")


@dataclass(frozen=True)
class Cell:
    """A value (number, text, bool, None) or a formula (text starting with `=`), with the style
    given for it; an empty style means the cell keeps what it has or what `like_row` gives it."""

    value: Any
    style: dict[str, Any] = field(default_factory=dict)
    note: str | None = None


@dataclass(frozen=True)
class Block:
    sheet: str
    row: int
    col: int
    cells: list[list[Cell]]
    like_row: int | None = None
    fill_down_to: int | None = None
    like: tuple[int, int] | None = None


def split_cell(ref: str) -> tuple[int, int]:
    """`B3` -> (row 3, column 2)."""
    from openpyxl.utils import column_index_from_string

    match = _CELL.fullmatch(ref.strip())
    if not match:
        raise ValueError(f"{ref!r} is not a cell address like 'B3'")
    return int(match.group(2)), column_index_from_string(match.group(1).upper())


def _hex(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError(f"{where}: a colour is six hex digits like '1F3864', got {value!r}")
    return value.lstrip("#").upper()


def _border(value: Any, where: str) -> dict[str, str]:
    sides = {side: value for side in _SIDES} if isinstance(value, str) else value
    if not isinstance(sides, dict) or not set(sides) <= set(_SIDES):
        raise ValueError(f"{where}: border is a style or {{side: style}} for {_SIDES}")
    for side, kind in sides.items():
        if kind not in _BORDER_STYLES:
            raise ValueError(f"{where}: border {side} must be one of {sorted(_BORDER_STYLES)}")
    return dict(sides)


def check_style(style: Any, where: str) -> dict[str, Any]:
    """A style's fields, validated: `bold` `italic` `underline` `wrap` (true/false), `color` and
    `fill` (hex), `font`, `size`, `num` (a number format), `align`, `valign`, `indent`, `border`."""
    if not isinstance(style, dict):
        raise ValueError(f"{where}: a style is an object of fields, got {style!r}")
    checked: dict[str, Any] = {}
    for key, value in style.items():
        if key in _FLAGS:
            checked[key] = bool(value)
        elif key in ("color", "fill"):
            checked[key] = _hex(value, f"{where}.{key}")
        elif key in ("font", "num"):
            checked[key] = str(value)
        elif key in ("size", "indent") and isinstance(value, int | float) and value >= 0:
            checked[key] = value
        elif key in _CHOICES and value in _CHOICES[key]:
            checked[key] = value
        elif key == "border":
            checked[key] = _border(value, f"{where}.border")
        else:
            raise ValueError(f"{where}: unknown or invalid style field {key}={value!r}")
    return checked


def _resolve(style: Any, named: dict[str, dict[str, Any]], where: str) -> dict[str, Any]:
    if style is None:
        return {}
    if isinstance(style, str):
        if style not in named:
            raise ValueError(f"{where}: no style named {style!r}; define it in `styles`")
        return named[style]
    return check_style(style, where)


def _cell(raw: Any, style: dict[str, Any], named: dict[str, dict[str, Any]], where: str) -> Cell:
    note = None
    if isinstance(raw, dict):
        unknown = set(raw) - {"v", "f", "s", "note"}
        if unknown or ("v" in raw and "f" in raw):
            raise ValueError(f"{where}: a cell object has `v` or `f`, and `s`, `note`")
        style = {**style, **_resolve(raw.get("s"), named, where)}
        note = raw.get("note")
        if "f" in raw:
            raw = str(raw["f"]) if str(raw["f"]).startswith("=") else "=" + str(raw["f"])
        else:
            raw = raw.get("v")
    if isinstance(raw, str) and raw.startswith("="):
        raw = _validate_and_normalize_formula(raw)
    elif isinstance(raw, str) and _ISO_DATE.fullmatch(raw):
        raw = _date(raw, where)
    elif raw is not None and not isinstance(raw, str | int | float | bool):
        raise ValueError(f"{where}: a cell is a number, text, true/false, null or an object")
    return Cell(raw, style, None if note is None else str(note))


def _date(text: str, where: str) -> dt.date | dt.datetime:
    """An ISO date is a real date, as Excel makes one of a typed date; a date without a time
    stays a date, so it shows without 00:00:00."""
    try:
        moment = dt.datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{where}: {text!r} looks like a date but is not one") from None
    return moment.date() if len(text) == 10 else moment


def _per_index(raw: Any, size: int, named: dict[str, Any], where: str) -> list[dict[str, Any]]:
    """`row_styles` / `col_styles`: a list by position, or an object keyed by position."""
    if raw is None:
        return [{} for _ in range(size)]
    items = enumerate(raw) if isinstance(raw, list) else ((int(k), v) for k, v in raw.items())
    styles: list[dict[str, Any]] = [{} for _ in range(size)]
    for index, style in items:
        if 0 <= index < size:
            styles[index] = _resolve(style, named, f"{where}[{index}]")
    return styles


def parse_block(raw: Any, named: dict[str, dict[str, Any]], where: str) -> Block:
    if not isinstance(raw, dict) or not isinstance(raw.get("rows"), list):
        raise ValueError(f"{where}: a block has `sheet`, `at` and `rows` (a list of rows)")
    sheet = str(raw.get("sheet") or "").strip()
    if not sheet or len(sheet) > 31 or any(c in sheet for c in "[]:*?/\\"):
        raise ValueError(f"{where}: a sheet name is 1-31 characters without []:*?/\\")
    row, col = split_cell(str(raw.get("at", "A1")))
    rows = [r if isinstance(r, list) else [r] for r in raw["rows"]]
    width = max((len(r) for r in rows), default=0)
    base = _resolve(raw.get("style"), named, f"{where}.style")
    by_row = _per_index(raw.get("row_styles"), len(rows), named, f"{where}.row_styles")
    by_col = _per_index(raw.get("col_styles"), width, named, f"{where}.col_styles")
    cells = [
        [
            _cell(value, {**base, **by_col[j], **by_row[i]}, named, f"{where}.rows[{i}][{j}]")
            for j, value in enumerate(values)
        ]
        for i, values in enumerate(rows)
    ]
    fill_down_to = raw.get("fill_down_to")
    if fill_down_to is not None and int(fill_down_to) < row + len(rows) - 1:
        raise ValueError(f"{where}: fill_down_to must be below the block's last row")
    like_row = raw.get("like_row")
    like = raw.get("like")
    if like_row is not None and like is not None:
        raise ValueError(f"{where}: give `like_row` (each column's look) or `like` (one cell's)")
    return Block(
        sheet,
        row,
        col,
        cells,
        None if like_row is None else int(like_row),
        None if fill_down_to is None else int(fill_down_to),
        None if like is None else split_cell(str(like)),
    )


def parse_blocks(blocks: Any, styles: Any = None) -> list[Block]:
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("`blocks` is a non-empty list of blocks")
    named = {
        str(name): check_style(style, f"styles.{name}") for name, style in (styles or {}).items()
    }
    return [parse_block(raw, named, f"blocks[{i}]") for i, raw in enumerate(blocks)]


# Each operation of `modify_xlsx`: the fields it needs and the ones it may have.
OPS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "add_sheet": (frozenset({"name"}), frozenset({"index", "tab_color"})),
    "rename_sheet": (frozenset({"sheet", "name"}), frozenset()),
    "delete_sheet": (frozenset({"sheet"}), frozenset()),
    "tab_color": (frozenset({"sheet", "color"}), frozenset()),
    "cols": (frozenset({"sheet", "cols"}), frozenset({"width", "hidden"})),
    "rows": (frozenset({"sheet", "rows"}), frozenset({"height", "hidden"})),
    "freeze": (frozenset({"sheet"}), frozenset({"at"})),
    "merge": (frozenset({"sheet", "range"}), frozenset({"undo"})),
    "chart": (
        frozenset({"sheet", "kind", "source", "at"}),
        frozenset({"title", "x_title", "y_title", "colors", "stacked", "labels", "size"}),
    ),
    "conditional": (
        frozenset({"sheet", "range", "rule"}),
        frozenset({"colors", "operator", "values", "formula", "fill", "color", "rank"}),
    ),
    "validation": (frozenset({"sheet", "range"}), frozenset({"list", "source", "message"})),
    "print": (
        frozenset({"sheet"}),
        frozenset({"landscape", "fit_width", "repeat_rows", "area"}),
    ),
    "name": (frozenset({"name", "ref"}), frozenset()),
}
CHART_KINDS = frozenset({"column", "bar", "line", "pie", "area", "scatter"})
CONDITIONAL_RULES = frozenset({"color_scale", "data_bar", "cell", "formula", "top"})


def _check_op_values(op: dict[str, Any], where: str) -> None:
    kind = op["op"]
    if kind == "chart" and op["kind"] not in CHART_KINDS:
        raise ValueError(f"{where}: chart kind is one of {sorted(CHART_KINDS)}")
    if kind == "conditional" and op["rule"] not in CONDITIONAL_RULES:
        raise ValueError(f"{where}: rule is one of {sorted(CONDITIONAL_RULES)}")
    if kind == "validation" and ("list" in op) == ("source" in op):
        raise ValueError(f"{where}: a validation has `list` (values) or `source` (a range)")
    for key in ("color", "fill", "tab_color"):
        if key in op:
            op[key] = _hex(op[key], f"{where}.{key}")
    if "colors" in op:
        op["colors"] = [_hex(c, f"{where}.colors") for c in op["colors"]]
    for key in ("at",):
        if key in op and op[key]:
            split_cell(str(op[key]))


def parse_ops(ops: Any) -> list[dict[str, Any]]:
    """`modify_xlsx`'s operations, each `{"op": name, ...}`, checked against `OPS`."""
    if not isinstance(ops, list) or not ops:
        raise ValueError("`ops` is a non-empty list of operations")
    parsed = []
    for i, raw in enumerate(ops):
        where = f"ops[{i}]"
        if not isinstance(raw, dict) or raw.get("op") not in OPS:
            raise ValueError(f"{where}: `op` is one of {sorted(OPS)}")
        needed, optional = OPS[raw["op"]]
        missing = needed - set(raw)
        unknown = set(raw) - needed - optional - {"op"}
        if missing or unknown:
            raise ValueError(
                f"{where} ({raw['op']}): missing {sorted(missing)}, unknown {sorted(unknown)}"
            )
        op = dict(raw)
        _check_op_values(op, where)
        parsed.append(op)
    return parsed
