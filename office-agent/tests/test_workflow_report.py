"""A run's report (decision 0030) and the task's autonomy ceiling, from step records alone."""

from __future__ import annotations

from typing import Any

import pytest

from coscribe.workflow_spec import parse_workflow
from coscribe.workflows import run_report

FILE = {"id": "file", "kind": "agent", "title": "File the row", "goal": "File {{row}}",
        "autonomy": "high", "save_as": "filed"}  # fmt: skip
EACH = {"id": "each", "kind": "loop", "title": "Each row", "over": "rows", "item": "row",
        "steps": [FILE]}  # fmt: skip
ROWS = {"id": "rows", "kind": "tool", "title": "Read the rows", "tool": "rows", "save_as": "rows"}


def _record(step_id: str, status: str, iteration: list[int], **more: Any) -> dict[str, Any]:
    return {"step_id": step_id, "status": status, "iteration": iteration, **more}


def test_the_report_says_what_was_done_not_done_and_decided() -> None:
    workflow = parse_workflow({"version": 2, "steps": [ROWS, EACH]})
    assumed = ["date: 02/11/2026 (form wants DD/MM)"]
    records = [
        _record("rows", "done", []),
        _record("file", "done", [0], agent={"tool_calls": 9, "tokens": 1200, "assumed": assumed}),
        _record(
            "file",
            "failed",
            [1],
            error="The agent stopped: no receipt",
            agent={"tool_calls": 4, "tokens": 300},
        ),  # fmt: skip
        _record("each", "failed", [], output={"done": 1, "total": 2, "items": ["a", "b"]}),
    ]

    report = run_report(workflow, records, "2026-10-31T10:00:00", "2026-10-31T10:02:30")

    assert report["autonomy"] == "proactive"
    assert report["loops"] == [{"step_id": "each", "title": "Each row", "done": 1, "total": 2}]
    assert [(n["step_id"], n["iteration"], n["error"]) for n in report["not_done"]] == [
        ("file", [1], "The agent stopped: no receipt"),
        ("each", [], None),
    ]
    assert report["assumed"] == [
        {"step_id": "file", "title": "File the row", "iteration": [0], "values": assumed}
    ]
    assert (report["tool_calls"], report["tokens"], report["seconds"]) == (13, 1500, 150.0)


def test_a_fixed_task_refuses_an_agent_step() -> None:
    with pytest.raises(ValueError, match='autonomy is fixed, which doesn\'t allow "File the row"'):
        parse_workflow({"version": 2, "autonomy": "fixed", "steps": [ROWS, EACH]})
    assert parse_workflow({"steps": [ROWS]}).effective_autonomy() == "fixed"
    full = {**FILE, "autonomy": "full", "goal": "File every row"}
    assert parse_workflow({"version": 2, "steps": [full]}).effective_autonomy() == "autonomous"
    assert parse_workflow({"version": 2, "autonomy": "proactive", "steps": [ROWS, EACH]})
