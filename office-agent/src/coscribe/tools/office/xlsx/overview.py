"""A sheet's layout in a few lines, for `read_xlsx`: what a model otherwise opens a script to see
(the header's look, each column's number format and formula, frozen panes, rules, charts) before
it adds to a user's table."""

from __future__ import annotations

from typing import Any

_LISTED = 8


def _look(cell: Any) -> str:
    parts = []
    if cell.font.bold:
        parts.append("bold")
    if cell.font.color is not None and isinstance(cell.font.color.rgb, str):
        if cell.font.color.rgb[-6:] not in ("000000",):
            parts.append(f"color {cell.font.color.rgb[-6:]}")
    if cell.fill is not None and cell.fill.fill_type == "solid":
        parts.append(f"fill {str(cell.fill.fgColor.rgb)[-6:]}")
    if cell.border.bottom is not None and cell.border.bottom.style:
        parts.append(f"bottom border {cell.border.bottom.style}")
    return ", ".join(parts) or "plain"


def _columns(sheet: Any, header: int) -> list[str]:
    """Per column below the header: its number format, and its first formula with how many
    cells hold a formula."""
    lines = []
    for column in sheet.iter_cols(min_row=header + 1, max_row=sheet.max_row):
        filled = [c for c in column if c.value not in (None, "")]
        if not filled:
            continue
        letter = filled[0].column_letter
        formats = sorted({c.number_format for c in filled if c.number_format != "General"})
        formulas = [c for c in filled if isinstance(c.value, str) and c.value.startswith("=")]
        if not formats and not formulas:
            continue
        text = f"{letter}{filled[0].row}:{letter}{filled[-1].row}"
        if formats:
            text += f" format {' | '.join(formats[:2])}"
        if formulas:
            text += (
                f"; {len(formulas)} formulas, first {formulas[0].coordinate} {formulas[0].value}"
            )
        lines.append(text)
    return lines[: _LISTED * 2]


def _objects(sheet: Any) -> list[str]:
    found = []
    if sheet.freeze_panes:
        found.append(f"frozen at {sheet.freeze_panes}")
    if sheet.merged_cells.ranges:
        found.append(
            "merged " + ", ".join(str(r) for r in list(sheet.merged_cells.ranges)[:_LISTED])
        )
    rules = [str(rng.sqref) for rng in sheet.conditional_formatting]
    if rules:
        found.append("conditional formats on " + ", ".join(rules[:_LISTED]))
    lists = [str(v.sqref) for v in sheet.data_validations.dataValidation]
    if lists:
        found.append("validations on " + ", ".join(lists[:_LISTED]))
    charts = getattr(sheet, "_charts", [])
    if charts:
        found.append(f"{len(charts)} chart(s)")
    widths = {
        letter: round(d.width, 1)
        for letter, d in sheet.column_dimensions.items()
        if d.customWidth and d.width
    }
    if widths:
        found.append(
            "widths " + " ".join(f"{k}={v}" for k, v in list(widths.items())[: _LISTED * 2])
        )
    return found


def sheet_layout(sheet: Any) -> str:
    """`Layout:` lines for one sheet; empty for an empty sheet."""
    if sheet.max_row == 1 and sheet.max_column == 1 and sheet["A1"].value is None:
        return ""
    header = next((r for r in range(1, sheet.max_row + 1) if any(c.value for c in sheet[r])), 1)
    first = next(c for c in sheet[header] if c.value not in (None, ""))
    lines = [f"used {sheet.dimensions}; header row {header} ({_look(first)})"]
    lines += _objects(sheet)
    lines += _columns(sheet, header)
    return "Layout:\n" + "\n".join(f"- {line}" for line in lines)
