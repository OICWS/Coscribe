"""Two data tasks a person repeats every month, the input files they read, the ways those files
drift, and what the right output is.

A drift changes what the rows mean (a new status, a duplicate, a split payment) or only how the
file is written (names, order, formats, encoding). The right output is computed from the rows,
so a report that is wrong after a drift is wrong by the same rule a person would apply."""

from __future__ import annotations

import csv
import io
import random
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

Row = dict[str, Any]


@dataclass(frozen=True)
class Written:
    """How a file is written: its column names and order, the separators, the date format,
    lines above the header, its encoding."""

    names: dict[str, str]
    order: list[str] | None = None
    delimiter: str = ","
    decimal_comma: bool = False
    date_format: str = "%Y-%m-%d"
    title_lines: tuple[str, ...] = ()
    encoding: str = "utf-8"


@dataclass(frozen=True)
class DataTask:
    slug: str
    brief: str
    # The input files, by name, built from the task's rows.
    files: Callable[[dict[str, list[Row]], frozenset[str]], dict[str, bytes]]
    rows: Callable[[frozenset[str]], dict[str, list[Row]]]
    expected: Callable[[dict[str, list[Row]]], list[dict[str, str]]]
    output: str
    key: str


def money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _cell(value: Any, written: Written) -> str:
    if isinstance(value, Decimal):
        text = money(value)
        if written.decimal_comma:
            whole, cents = text.split(".")
            groups = f"{int(whole):,}".replace(",", ".")
            text = f"{groups},{cents}"
        return text
    if hasattr(value, "strftime"):
        return str(value.strftime(written.date_format))
    return "" if value is None else str(value)


def write_csv(rows: list[Row], columns: list[str], written: Written) -> bytes:
    order = written.order or columns
    out = io.StringIO()
    for line in written.title_lines:
        out.write(line + "\n")
    writer = csv.writer(out, delimiter=written.delimiter, lineterminator="\n")
    writer.writerow([written.names.get(c, c) for c in order])
    for row in rows:
        writer.writerow([_cell(row.get(c), written) for c in order])
    return out.getvalue().encode(written.encoding)


def _written(mutations: frozenset[str], renames: dict[str, str], order: list[str]) -> Written:
    european = "decimal_comma" in mutations
    return Written(
        names=renames if "rename" in mutations else {},
        order=order if "reorder" in mutations else None,
        delimiter=";" if european else ",",
        decimal_comma=european,
        date_format="%d.%m.%Y" if "date_format" in mutations else "%Y-%m-%d",
        title_lines=("Export", "Created 01.11.2026", "") if "title_rows" in mutations else (),
        encoding="cp1252" if "encoding" in mutations else "utf-8",
    )


# -- Monthly sales summary ---------------------------------------------------------------------

SALES_COLUMNS = ["order_id", "date", "region", "product", "quantity", "unit_price", "status"]
_REGIONS = ["East", "North", "South", "West"]
_PRODUCTS = ["Barcode scanner", "Label printer", "Thermal labels", "Docking station"]


def sales_rows(mutations: frozenset[str]) -> dict[str, list[Row]]:
    from datetime import date

    rnd = random.Random(754)
    rows: list[Row] = []
    for n in range(36):
        late = n % 9 == 4  # a September order booked late: not this month's
        rows.append(
            {
                "order_id": f"SO-{1001 + n}",
                "date": date(2026, 9, 28 + n % 3) if late else date(2026, 10, 1 + n % 28),
                "region": rnd.choice(_REGIONS),
                "product": rnd.choice(_PRODUCTS),
                "quantity": rnd.randint(1, 12),
                "unit_price": Decimal(rnd.choice([1234.5, 89.9, 12.5, 249.0, 7.25])).quantize(
                    Decimal("0.01")
                ),
                "status": "refunded" if n % 7 == 3 else "paid",
            }
        )
    if "new_status" in mutations:
        for row in rows[2::10]:
            row["status"] = "cancelled"
    if "duplicates" in mutations:
        rows += [dict(rows[5]), dict(rows[17]), dict(rows[30])]
    if "encoding" in mutations:
        for row in rows[::4]:
            row["region"] = "Zürich"
    if "missing" in mutations:
        for row in (rows[6], rows[20]):
            row["quantity"] = None
    return {"orders.csv": rows}


def sales_files(rows: dict[str, list[Row]], mutations: frozenset[str]) -> dict[str, bytes]:
    renames = {"region": "sales_region", "quantity": "qty", "unit_price": "price_eur"}
    order = ["status", "product", "order_id", "unit_price", "quantity", "region", "date"]
    return {
        "orders.csv": write_csv(
            rows["orders.csv"], SALES_COLUMNS, _written(mutations, renames, order)
        )
    }


def sales_expected(rows: dict[str, list[Row]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    totals: dict[str, tuple[int, Decimal]] = {}
    for row in rows["orders.csv"]:
        if row["order_id"] in seen:
            continue
        seen.add(row["order_id"])
        if row["status"] != "paid" or (row["date"].year, row["date"].month) != (2026, 10):
            continue
        count, revenue = totals.get(row["region"], (0, Decimal(0)))
        totals[row["region"]] = (count + 1, revenue + row["quantity"] * row["unit_price"])
    report = [
        {"region": r, "orders": str(c), "revenue": money(v)} for r, (c, v) in sorted(totals.items())
    ]
    all_orders = sum(c for c, _ in totals.values())
    all_revenue = sum((v for _, v in totals.values()), Decimal(0))
    return [*report, {"region": "Total", "orders": str(all_orders), "revenue": money(all_revenue)}]


SALES = DataTask(
    slug="sales",
    brief=(
        "Every month the shop system exports this month's orders to evals/data/sales/orders.csv. "
        "Make the monthly summary from it: write evals/data/sales/report.csv with the columns "
        "region, orders and revenue -- one row per region with the number of paid orders dated "
        "in October 2026 and their revenue (quantity times unit price, rounded to cents), sorted "
        "by region, then a last row named Total. Only paid orders count; an order listed twice "
        "counts once."
    ),
    files=sales_files,
    rows=sales_rows,
    expected=sales_expected,
    output="evals/data/sales/report.csv",
    key="region",
)


# -- Invoice reconciliation -------------------------------------------------------------------

INVOICE_COLUMNS = ["invoice", "customer", "amount", "due_date"]
BANK_COLUMNS = ["booking_date", "text", "amount"]
_CUSTOMERS = ["Acme GmbH", "Brandt Logistik", "Atelier Moreau", "Nordlicht AG", "Keller & Söhne"]


def reconcile_rows(mutations: frozenset[str]) -> dict[str, list[Row]]:
    from datetime import date, timedelta

    rnd = random.Random(768)
    invoices: list[Row] = []
    bank: list[Row] = []
    for n in range(15):
        number = f"2026-{101 + n:04d}"
        amount = Decimal(rnd.randint(200, 9000)) + Decimal(rnd.randint(0, 99)) / 100
        customer = _CUSTOMERS[n % len(_CUSTOMERS)]
        invoices.append({"invoice": f"INV-{number}", "customer": customer, "amount": amount,
                         "due_date": date(2026, 10, 1) + timedelta(days=2 * n)})  # fmt: skip
        if n in (3, 9, 13):
            continue  # unpaid
        paid = amount - Decimal("150.00") if n == 6 else amount  # a short payment
        reference = (
            f"invoice no. {number} {customer}"
            if "reference_format" in mutations
            else f"Payment INV-{number} {customer}"
        )
        when = date(2026, 10, 3) + timedelta(days=n)
        if "split_payment" in mutations and n == 11:
            half = (paid / 2).quantize(Decimal("0.01"))
            bank.append({"booking_date": when, "text": reference + " part 1", "amount": half})
            bank.append(
                {"booking_date": when, "text": reference + " part 2", "amount": paid - half}
            )
        else:
            bank.append({"booking_date": when, "text": reference, "amount": paid})
    bank.insert(4, {"booking_date": date(2026, 10, 9), "text": "Account fee October",
                    "amount": Decimal("-12.90")})  # fmt: skip
    bank.insert(9, {"booking_date": date(2026, 10, 15), "text": "Rent office Hamburg",
                    "amount": Decimal("-2450.00")})  # fmt: skip
    if "missing" in mutations:
        invoices[9]["amount"] = None
    return {"invoices.csv": invoices, "bank.csv": bank}


def reconcile_files(rows: dict[str, list[Row]], mutations: frozenset[str]) -> dict[str, bytes]:
    bank_written = _written(
        mutations,
        {"booking_date": "Buchungstag", "text": "Verwendungszweck", "amount": "Betrag"},
        ["amount", "booking_date", "text"],
    )
    bank_columns = BANK_COLUMNS
    bank_rows = rows["bank.csv"]
    if "debit_credit" in mutations:
        bank_columns = ["booking_date", "text", "debit", "credit"]
        bank_rows = [
            {**r, "debit": -r["amount"] if r["amount"] < 0 else None,
             "credit": r["amount"] if r["amount"] >= 0 else None}
            for r in bank_rows
        ]  # fmt: skip
        bank_written = Written(**{**bank_written.__dict__, "order": None})
    # Only the bank export drifts; the invoice list comes from the person's own system.
    invoice_written = Written(names={})
    return {
        "invoices.csv": write_csv(rows["invoices.csv"], INVOICE_COLUMNS, invoice_written),
        "bank.csv": write_csv(bank_rows, bank_columns, bank_written),
    }


def reconcile_expected(rows: dict[str, list[Row]]) -> list[dict[str, str]]:
    paid: dict[str, Decimal] = {}
    for line in rows["bank.csv"]:
        for invoice in rows["invoices.csv"]:
            number = invoice["invoice"].removeprefix("INV-")
            if number in line["text"]:
                paid[invoice["invoice"]] = paid.get(invoice["invoice"], Decimal(0)) + line["amount"]
    out = []
    for invoice in sorted(rows["invoices.csv"], key=lambda i: i["invoice"]):
        open_amount = invoice["amount"] - paid.get(invoice["invoice"], Decimal(0))
        if open_amount > Decimal("0.005"):
            out.append({"invoice": invoice["invoice"], "customer": invoice["customer"],
                        "outstanding": money(open_amount)})  # fmt: skip
    return out


RECONCILE = DataTask(
    slug="reconcile",
    brief=(
        "Every month I get our open invoices in evals/data/reconcile/invoices.csv and the bank "
        "export in evals/data/reconcile/bank.csv. Find what is still unpaid: write "
        "evals/data/reconcile/unpaid.csv with the columns invoice, customer and outstanding -- "
        "one row per invoice not fully paid, with the amount still open, sorted by invoice. A "
        "payment names its invoice number in the booking text; one invoice can be paid in "
        "parts."
    ),
    files=reconcile_files,
    rows=reconcile_rows,
    expected=reconcile_expected,
    output="evals/data/reconcile/unpaid.csv",
    key="invoice",
)

DATA_TASKS = {t.slug: t for t in (SALES, RECONCILE)}

# Changes one at a time, then pairs; `missing` must stop the run.
DATA_MUTATIONS: dict[str, list[tuple[str, ...]]] = {
    "sales": [
        (),
        ("rename",),
        ("reorder", "title_rows"),
        ("date_format", "decimal_comma"),
        ("new_status", "duplicates"),
        ("encoding",),
        ("missing",),
    ],
    "reconcile": [
        (),
        ("rename",),
        ("reference_format",),
        ("decimal_comma", "title_rows"),
        ("debit_credit", "split_payment"),
        ("date_format",),
        ("missing",),
    ],
}


def _number(text: str) -> Decimal | None:
    text = text.strip().replace(" ", "").replace("€", "")
    if "," in text and "." in text:
        text = (
            text.replace(".", "").replace(",", ".")
            if text.rfind(",") > text.rfind(".")
            else (text.replace(",", ""))
        )
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except ArithmeticError:
        return None


def read_output(data: bytes) -> list[dict[str, str]]:
    """The rows of a CSV the workflow wrote, its header lower-cased, whatever its separator."""
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect: Any = csv.Sniffer().sniff(text.splitlines()[0] if text else ",", ",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return [
        {str(k).strip().lower(): str(v or "").strip() for k, v in row.items() if k is not None}
        for row in reader
    ]


def judge_output(got: list[dict[str, str]], want: list[dict[str, str]], key: str) -> list[str]:
    """What differs between the report written and the right one; [] when it is right. Order
    matters only in that every wanted row is there once; extra columns are ignored."""
    problems: list[str] = []
    left = list(got)
    for row in want:
        match = next((g for g in left if g.get(key, "").casefold() == row[key].casefold()), None)
        if match is None:
            problems.append(f"{row[key]}: missing")
            continue
        left.remove(match)
        for name, value in row.items():
            if name == key:
                continue
            have, need = _number(match.get(name, "")), _number(value)
            same = have == need if need is not None else match.get(name, "") == value
            if not same:
                problems.append(f"{row[key]}: {name} {match.get(name, '')!r}, should be {value}")
    problems += [f"extra row {g.get(key, '?')}" for g in left]
    return problems
