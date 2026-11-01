"""The data eval's deterministic parts: the files each drift writes, the right answer computed
from the rows, and the judge of the file a workflow wrote. The runs themselves need a model."""

from __future__ import annotations

from evals.workflow.data_run import DataOutcome, summary, verdict
from evals.workflow.data_tasks import (
    DATA_MUTATIONS,
    DATA_TASKS,
    RECONCILE,
    SALES,
    judge_output,
    read_output,
)


def _files(task, *mutations: str) -> dict[str, bytes]:  # type: ignore[no-untyped-def]
    ms = frozenset(mutations)
    return dict(task.files(task.rows(ms), ms))


def test_a_drift_in_how_the_file_is_written_keeps_the_right_answer() -> None:
    original = SALES.expected(SALES.rows(frozenset()))
    for mutations in (("rename",), ("reorder", "title_rows"), ("date_format", "decimal_comma")):
        assert SALES.expected(SALES.rows(frozenset(mutations))) == original
    written = _files(SALES, "rename", "decimal_comma", "date_format")["orders.csv"].decode()
    header, first = written.splitlines()[:2]
    assert header == "order_id;date;sales_region;product;qty;price_eur;status"
    assert ";2026-" not in first and ".10.2026;" in first
    assert "1.234,50" in written


def test_a_drift_in_what_the_rows_mean_changes_it() -> None:
    original = SALES.expected(SALES.rows(frozenset()))
    drifted = SALES.expected(SALES.rows(frozenset({"new_status", "duplicates"})))
    # Cancelled orders don't count, and a duplicate counts once.
    assert int(drifted[-1]["orders"]) < int(original[-1]["orders"])
    assert "cancelled" in _files(SALES, "new_status")["orders.csv"].decode()
    encoded = _files(SALES, "encoding")["orders.csv"]
    assert "Zürich" in encoded.decode("cp1252")
    assert any(row["region"] == "Zürich" for row in SALES.expected(SALES.rows({"encoding"})))  # type: ignore[arg-type]


def test_a_split_payment_and_a_new_booking_text_still_settle_their_invoices() -> None:
    original = RECONCILE.expected(RECONCILE.rows(frozenset()))
    assert [r["invoice"] for r in original] == [
        "INV-2026-0104", "INV-2026-0107", "INV-2026-0110", "INV-2026-0114",
    ]  # fmt: skip
    assert original[1]["outstanding"] == "150.00"  # the short payment
    for mutations in (("reference_format",), ("debit_credit", "split_payment")):
        assert RECONCILE.expected(RECONCILE.rows(frozenset(mutations))) == original
    bank = _files(RECONCILE, "debit_credit", "split_payment")["bank.csv"].decode()
    assert bank.splitlines()[0] == "booking_date,text,debit,credit"
    assert "part 2" in bank


def test_the_judge_reads_any_separator_and_names_what_is_wrong() -> None:
    want = SALES.expected(SALES.rows(frozenset()))
    lines = ["Region;Orders;Revenue"] + [
        f"{r['region']};{r['orders']};{r['revenue'].replace('.', ',')}" for r in want
    ]
    assert judge_output(read_output("\n".join(lines).encode()), want, "region") == []
    wrong = [dict(r) for r in want[:-1]]
    wrong[0]["revenue"] = "1.00"
    problems = judge_output(wrong, want, "region")
    assert problems[0].startswith(f"{want[0]['region']}: revenue '1.00'")
    assert problems[-1] == "Total: missing"


def test_a_completed_run_with_a_wrong_report_is_a_false_success() -> None:
    o = DataOutcome("sales/drafted/new_status+duplicates", 1, status="completed",
                    problems=["East: orders '9', should be 8"])  # fmt: skip
    assert verdict(o, must_stop=False, wrote=True) == "FALSE_SUCCESS"
    stopped = DataOutcome("sales/drafted/missing", 1, status="failed")
    assert verdict(stopped, must_stop=True, wrote=False) == "SAFE_STOP"
    assert verdict(stopped, must_stop=True, wrote=True) == "GUESSED"


def test_pass_k_needs_every_repeat_right() -> None:
    runs = [
        DataOutcome("sales/agent/original", 1, verdict="PASS"),
        DataOutcome("sales/agent/original", 2, verdict="FALSE_SUCCESS"),
        DataOutcome("sales/agent/rename", 1, verdict="PASS"),
        DataOutcome("sales/agent/rename", 2, verdict="PASS"),
    ]
    table = summary(runs)
    assert "| agent | 4 | 75% | 50% | 1 | 0 |" in table


def test_every_task_has_its_scenarios() -> None:
    assert set(DATA_MUTATIONS) == set(DATA_TASKS)
    assert all(("missing",) in sets for sets in DATA_MUTATIONS.values())


def test_a_run_parked_on_a_person_is_asking_not_stopping() -> None:
    parked = DataOutcome(
        "sales/agent/missing", 1, status="needs_approval", problems=["no file written"]
    )
    assert verdict(parked, must_stop=True, wrote=False) == "ASKED"
    assert verdict(parked, must_stop=False, wrote=False) == "ASKED"
