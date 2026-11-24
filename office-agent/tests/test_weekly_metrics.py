"""`scripts/weekly_metrics.py`: the pieces that turn a week of GitHub data into numbers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "weekly_metrics.py"


@pytest.fixture(scope="module")
def metrics() -> ModuleType:
    spec = importlib.util.spec_from_file_location("weekly_metrics", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["weekly_metrics"] = module
    spec.loader.exec_module(module)
    return module


def _run(created: str, updated: str, conclusion: str) -> dict[str, str]:
    return {"created_at": created, "updated_at": updated, "conclusion": conclusion}


def test_an_iso_week_runs_from_monday_to_the_next_monday(metrics: ModuleType) -> None:
    start, end = metrics.week_bounds("2026-W42")

    assert start == datetime(2026, 10, 12, tzinfo=UTC)
    assert end - start == timedelta(days=7)


def test_main_is_red_from_a_failed_run_to_the_next_green_one(metrics: ModuleType) -> None:
    start, end = metrics.week_bounds("2026-W42")
    runs = [
        _run("2026-10-13T10:00:00Z", "2026-10-13T10:10:00Z", "success"),
        _run("2026-10-14T10:00:00Z", "2026-10-14T10:08:00Z", "failure"),
        _run("2026-10-14T11:00:00Z", "2026-10-14T11:09:00Z", "failure"),
        _run("2026-10-14T12:00:00Z", "2026-10-14T12:05:00Z", "success"),
    ]

    assert metrics.red_time(runs, start, end) == timedelta(hours=2, minutes=5)


def test_a_main_still_red_at_the_end_counts_to_the_end(metrics: ModuleType) -> None:
    start, end = metrics.week_bounds("2026-W42")
    runs = [_run("2026-10-18T12:00:00Z", "2026-10-18T12:05:00Z", "failure")]

    assert metrics.red_time(runs, start, end) == timedelta(hours=12)


def test_the_ledger_counts_entries_with_a_not_verified_item(
    metrics: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "2026-10-07-old.md").write_text("## Not verified\n- x\n", encoding="utf-8")
    (tmp_path / "2026-10-09-a.md").write_text("## Not verified\n- a run\n", encoding="utf-8")
    (tmp_path / "2026-10-10-b.md").write_text("## Not verified\n- none\n", encoding="utf-8")
    (tmp_path / "2026-10-11-c.md").write_text("# no section\n", encoding="utf-8")

    assert metrics.ledger(tmp_path, since="2026-10-08") == {"entries": 3, "with_not_verified": 1}


def test_the_ratchet_trend_says_n_a_without_history(metrics: ModuleType) -> None:
    after = {"fan_out": {"a": 26}, "long_functions": {"f": 120, "g": 130}}

    assert metrics.ratchet_trend(None, after) == [
        "| fan_out | n/a | 1 | n/a |",
        "| long_functions | n/a | 2 | n/a |",
    ]
    assert metrics.ratchet_trend({"fan_out": {"a": 26, "b": 27}}, after) == [
        "| fan_out | 2 | 1 | -1 |",
        "| long_functions | 0 | 2 | +2 |",
    ]


def test_the_selection_share_counts_a_full_run_as_the_whole_suite(metrics: ModuleType) -> None:
    plans = {
        "a": ("selected", ["tests/test_a.py"]),
        "b": ("full", []),
        "c": ("docs", ["tests/test_doc_files.py", "tests/test_doc_freshness.py"]),
    }
    lines = metrics.selection([["a"], ["b"], ["c"]], lambda files: plans[files[0]], 10)
    assert lines == [
        "- scope of the 3 merged pull requests: 1 selected, 1 full, 1 docs only",
        "- share of the 10 test files they ran: mean 43%, median 20%",
    ]
    assert metrics.selection([], lambda files: plans["a"], 10) == [
        "- no merged pull request this week"
    ]


def test_a_failed_audit_night_is_named_as_a_miss(metrics: ModuleType) -> None:
    runs = [{"conclusion": "success"}, {"conclusion": "failure"}, {"conclusion": "cancelled"}]
    assert metrics.audit_line(runs) == (
        "- nightly selection audit: 2 runs, 1 failed (a test that fails was not selected)"
    )
    assert metrics.audit_line(runs[:1]) == "- nightly selection audit: 1 runs, 0 failed (no miss)"
    assert metrics.audit_line([]) == "- nightly selection audit: no run this week"


def test_the_budgets_name_the_core_the_largest_and_those_near_the_limit(
    metrics: ModuleType,
) -> None:
    budgets = {"core_lines": 1000, "component_lines": 100}
    sizes = {"web": 300, "tools": 85, "pptx": 95, "small": 10}
    assert metrics.budget_lines(budgets, sizes, frozenset({"web", "small"})) == [
        "- core: 310 of 1000 lines (31%)",
        "- largest component: web, 300 of 100 lines",
        "- near its budget: web (300 lines, 300%)",
        "- near its budget: pptx (95 lines, 95%)",
        "- near its budget: tools (85 lines, 85%)",
    ]


def test_the_cards_furthest_behind_their_code_come_first(metrics: ModuleType) -> None:
    behind = {"web": 3, "runtime": 9, "tools": 0, "cli": 3}
    assert metrics.card_lines(behind, listed=3) == [
        "- runtime: 9 commits since its card changed",
        "- cli: 3 commits since its card changed",
        "- web: 3 commits since its card changed",
    ]
    assert metrics.card_lines({"tools": 0}) == [
        "- every card changed with its code's latest commit"
    ]
