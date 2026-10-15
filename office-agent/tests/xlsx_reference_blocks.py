"""The reference solutions of the Excel tasks again, written only through the block and object
operations (decision 0011): every task can be solved with them, and the result passes the same
checks as the openpyxl-built references in `xlsx_reference.py`."""

from __future__ import annotations

import csv
import datetime as dt
import shutil
from pathlib import Path

from coscribe.tools.office.xlsx.build import modify_workbook, write_cells

_HEAD = {"bold": True}


def _csv(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def clean_csv(inputs: Path, out: Path) -> Path:
    rows = [[c.strip() for c in r] for r in _csv(inputs / "orders_export.csv") if any(r)]
    header, seen, parsed = rows[0], set(), []
    for date, customer, category, amount in rows[1:]:
        for pattern in ("%Y/%m/%d", "%d %b %Y", "%Y-%m-%d"):
            try:
                day = dt.datetime.strptime(date, pattern).date()
                break
            except ValueError:
                continue
        key = (day, customer, category.title(), amount)
        if key not in seen:
            seen.add(key)
            number = float(amount.replace("$", "").replace(",", ""))
            parsed.append([day.isoformat(), customer, category.title(), number])
    parsed.sort(key=lambda r: r[0])
    path = out / "orders_clean.xlsx"
    write_cells(
        path,
        [
            {
                "sheet": "Orders",
                "row_styles": [_HEAD],
                "col_styles": [{"num": "yyyy-mm-dd"}, None, None, {"num": "#,##0.00"}],
                "rows": [header, *parsed],
            }
        ],
    )
    return path


def monthly_summary(inputs: Path, out: Path) -> Path:
    path = out / "transactions.xlsx"
    shutil.copyfile(inputs / "transactions.xlsx", path)

    def month(row: int, n: int) -> str:
        return (
            f"=SUMIFS(Data!$C$2:$C$15,Data!$B$2:$B$15,$A{row},"
            f'Data!$A$2:$A$15,">="&DATE(2026,{n},1),Data!$A$2:$A$15,"<"&DATE(2026,{n + 1},1))'
        )

    rows: list[list[object]] = [["Category", "Jan", "Feb", "Mar", "Total"]]
    for row, category in enumerate(["Food", "Rent", "Transport"], start=2):
        rows.append([category, month(row, 1), month(row, 2), month(row, 3), f"=SUM(B{row}:D{row})"])
    rows.append(["Total", *[f"=SUM({c}2:{c}4)" for c in "BCDE"]])
    write_cells(path, [{"sheet": "Summary", "row_styles": [_HEAD], "rows": rows}])
    return path


def lookup_two_sheets(inputs: Path, out: Path) -> Path:
    path = out / "shop.xlsx"
    shutil.copyfile(inputs / "shop.xlsx", path)
    write_cells(
        path,
        [
            {
                "sheet": "Orders",
                "at": "D1",
                "like": "C1",
                "rows": [["Product", "Unit price", "Line total"]],
            },
            {
                "sheet": "Orders",
                "at": "D2",
                "rows": [
                    [
                        "=VLOOKUP(B2,Prices!$A$2:$C$7,2,FALSE)",
                        "=VLOOKUP(B2,Prices!$A$2:$C$7,3,FALSE)",
                        "=E2*C2",
                    ]
                ],
                "col_styles": [None, {"num": "0.00"}, {"num": "0.00"}],
                "fill_down_to": 9,
            },
            {"sheet": "Orders", "at": "E11", "rows": [["Total", "=SUM(F2:F9)"]]},
        ],
    )
    return path


def line_chart(inputs: Path, out: Path) -> Path:
    rows = _csv(inputs / "monthly_visits.csv")
    path = out / "visits.xlsx"
    write_cells(
        path,
        [
            {
                "sheet": "Data",
                "row_styles": [_HEAD],
                "rows": [rows[0], *[[m, int(v)] for m, v in rows[1:]]],
            }
        ],
    )
    modify_workbook(
        path,
        [
            {
                "op": "chart",
                "sheet": "Data",
                "kind": "line",
                "source": "A1:B13",
                "at": "D2",
                "title": "Monthly visitors",
                "x_title": "Month",
                "y_title": "Visitors",
            }
        ],
    )
    return path


def edit_budget(inputs: Path, out: Path) -> Path:
    path = out / "budget_q1.xlsx"
    shutil.copyfile(inputs / "budget_q1.xlsx", path)
    write_cells(
        path,
        [
            {"sheet": "Budget", "at": "D1", "like": "C1", "rows": [["Variance"]]},
            {"sheet": "Budget", "at": "D2", "like": "C2", "rows": [["=C2-B2"]], "fill_down_to": 7},
            {
                "sheet": "Budget",
                "at": "A8",
                "like_row": 7,
                "rows": [["Total", "=SUM(B2:B7)", "=SUM(C2:C7)", "=SUM(D2:D7)"]],
            },
        ],
    )
    return path


def budget_model(inputs: Path, out: Path) -> Path:
    path = out / "budget_model.xlsx"
    rows: list[list[object]] = [
        ["Inputs", None],
        ["Units sold", 1000],
        ["Price per unit", 25],
        ["Cost per unit", 14],
        ["Fixed costs", 6000],
        ["Results", None],
        ["Revenue", "=B2*B3"],
        ["Variable costs", "=B2*B4"],
        ["Gross profit", "=B7-B8"],
        ["Net profit", "=B9-B5"],
        ["Net margin", {"f": "=B10/B7", "s": {"num": "0.0%"}}],
    ]
    write_cells(path, [{"sheet": "Model", "row_styles": {0: _HEAD, 5: _HEAD}, "rows": rows}])
    return path


def chinese_formats(inputs: Path, out: Path) -> Path:
    rows: list[list[object]] = [["区域", "销售额（元）", "销售额（万元）", "占比"]]
    for index, (region, amount) in enumerate(_csv(inputs / "各区域销售.csv")[1:], start=2):
        rows.append([region, int(amount), f"=B{index}/10000", f"=B{index}/$B$7"])
    rows.append(["合计", "=SUM(B2:B6)", "=B7/10000", "=B7/$B$7"])
    path = out / "区域销售汇总.xlsx"
    write_cells(
        path,
        [
            {
                "sheet": "汇总",
                "row_styles": [_HEAD],
                "col_styles": [
                    None,
                    {"num": '#,##0"元"'},
                    {"num": '#,##0.00"万"'},
                    {"num": "0.0%"},
                ],
                "rows": rows,
            }
        ],
    )
    return path


def validation_list(inputs: Path, out: Path) -> Path:
    path = out / "tickets.xlsx"
    shutil.copyfile(inputs / "tickets.xlsx", path)
    write_cells(
        path,
        [
            {"sheet": "Tickets", "at": "C2", "rows": [["Open"]] * 10},
            {"sheet": "Tickets", "at": "G1", "rows": [["Open tickets", '=COUNTIF(C2:C11,"Open")']]},
        ],
    )
    modify_workbook(
        path,
        [
            {
                "op": "validation",
                "sheet": "Tickets",
                "range": "C2:C11",
                "list": ["Open", "In progress", "Done"],
            }
        ],
    )
    return path


def sales_report(inputs: Path, out: Path) -> Path:
    ledger = _csv(inputs / "销售明细.csv")
    last = len(ledger)
    path = out / "销售分析.xlsx"

    def total(column: str, row: int) -> str:
        return f"=SUMIF(明细!{column}$2:{column}${last},$A{row},明细!$F$2:$F${last})"

    write_cells(
        path,
        [
            {
                "sheet": "汇总",
                "row_styles": [_HEAD],
                "col_styles": [None, {"num": "#,##0"}],
                "rows": [
                    ["区域", "销售额"],
                    *[
                        [r, total("B", i)]
                        for i, r in enumerate(["华东", "华南", "华北", "西南"], 2)
                    ],
                    ["合计", "=SUM(B2:B5)"],
                ],
            },
            {
                "sheet": "汇总",
                "at": "A8",
                "row_styles": [_HEAD],
                "col_styles": [None, {"num": "#,##0"}],
                "rows": [
                    ["产品线", "销售额"],
                    *[
                        [p, total("C", i)]
                        for i, p in enumerate(["智能门锁", "扫地机器人", "空气净化器"], 9)
                    ],
                ],
            },
            {
                "sheet": "明细",
                "row_styles": [_HEAD],
                "rows": [ledger[0], *[[*r[:3], *map(int, r[3:])] for r in ledger[1:]]],
            },
        ],
    )
    modify_workbook(
        path,
        [
            {
                "op": "chart",
                "sheet": "汇总",
                "kind": "column",
                "source": "A1:B5",
                "at": "D2",
                "title": "各区域销售额",
            }
        ],
    )
    return path


def store_forecast(inputs: Path, out: Path) -> Path:
    path = out / "门店盈利预测.xlsx"
    inputs_block = [
        ["门店数", 5],
        ["每店月营收（元）", 300000],
        ["年增长", {"v": 0.08, "s": {"num": "0%"}}],
        ["毛利率", {"v": 0.55, "s": {"num": "0%"}}],
        ["人工（每店每月）", 60000],
        ["房租（每店每月）", 40000],
        ["总部费用（每年）", 1200000],
    ]
    write_cells(
        path,
        [
            {"sheet": "模型", "col_styles": [None, {"color": "0000FF"}], "rows": inputs_block},
            {
                "sheet": "模型",
                "at": "A9",
                "row_styles": [_HEAD],
                "style": {"num": "#,##0"},
                "rows": [
                    ["", "第1年", "第2年", "第3年"],
                    ["营收", "=$B$1*$B$2*12", "=B10*(1+$B$3)", "=C10*(1+$B$3)"],
                    ["毛利", "=B10*$B$4", "=C10*$B$4", "=D10*$B$4"],
                    ["费用", *["=$B$1*($B$5+$B$6)*12+$B$7"] * 3],
                    ["净利润", "=B11-B12", "=C11-C12", "=D11-D12"],
                ],
            },
        ],
    )
    return path


SOLUTIONS = {
    "01-clean-csv": clean_csv,
    "02-monthly-summary": monthly_summary,
    "03-lookup-two-sheets": lookup_two_sheets,
    "04-line-chart": line_chart,
    "05-edit-budget": edit_budget,
    "06-budget-model": budget_model,
    "07-chinese-formats": chinese_formats,
    "08-validation-list": validation_list,
    "09-sales-report": sales_report,
    "10-store-forecast": store_forecast,
}
