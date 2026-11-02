"""Decision 0033: a workflow run that pauses for a person (an ask step) or for a time or a file
(a wait step), holding nothing while it waits, and goes on when answered or woken."""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from coscribe.workflow_spec import parse_workflow, workflow_error
from coscribe.workflows import (
    answer_problem,
    pause_steps,
    paused_at,
    run_report,
    run_test,
    wake_due,
)
from coscribe.workflows.engine import StepContext, StepRecord, WorkflowRun

NOW = datetime(2026, 11, 2, 9, 0)


def _problem(data: dict[str, Any]) -> str | None:
    try:
        parse_workflow(data)
    except ValidationError as exc:
        return workflow_error(exc, data)
    return None


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[datetime]:
    now = [NOW]
    monkeypatch.setattr(pause_steps, "clock", lambda: now[0])
    return now


def _settled(path: Path, text: str = "x") -> None:
    """A file that has stopped changing, as a finished download is."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    past = time.time() - pause_steps.FILE_SETTLE_SECONDS - 5
    os.utime(path, (past, past))


class Run:
    def __init__(self, tmp_path: Path, steps: list[dict[str, Any]], **workflow: Any) -> None:
        self.written: list[str] = []
        self.records: list[StepRecord] = []
        self.ctx = StepContext(
            tools={"write_file": self.write_file},
            workspace_root=tmp_path,
            state_dir=tmp_path,
            make_model=lambda _name: None,
        )
        self.workflow = parse_workflow({"steps": steps, **workflow})
        self.run = WorkflowRun(self.workflow, self.ctx, InMemorySaver(), "t", self.on_step)

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        self.written.append(content)
        return {"path": path}

    async def on_step(self, record: StepRecord) -> None:
        self.records.append(record)

    def statuses(self) -> list[tuple[str, str]]:
        return [(r.step_id, r.status) for r in self.records if r.status != "running"]


def _ask(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "ask", "kind": "ask", "title": "Ask for the amount",
        "message": "How much for {{who}}?", "save_as": "got",
        "fields": [{"name": "amount", "label": "Amount", "type": "number"},
                   {"name": "note", "type": "text", "required": False}],
        **overrides,
    }  # fmt: skip


def _write(text: str) -> dict[str, Any]:
    return {"id": "write", "kind": "tool", "title": "Write", "tool": "write_file",
            "args": {"path": "out.txt", "content": text}}  # fmt: skip


# -- the definition --


def test_an_ask_step_names_each_value_once_and_needs_defaults_to_go_on_without_an_answer() -> None:
    twice = [{"name": "a"}, {"name": "a"}]
    who = [{"name": "who"}]
    assert "own name" in str(_problem({"inputs": who, "steps": [_ask(fields=twice)]}))
    no_default = _ask(timeout_hours=2, on_timeout="defaults")
    assert "needs one for amount" in str(_problem({"inputs": who, "steps": [no_default]}))
    with_default = _ask(
        timeout_hours=2,
        on_timeout="defaults",
        fields=[{"name": "amount", "type": "number", "default": 5}],
    )
    assert _problem({"inputs": who, "steps": [with_default]}) is None


def test_a_pick_field_reads_a_list_from_before_it() -> None:
    pick = _ask(message="Which?",
                fields=[{"name": "rows", "type": "pick", "items": "rows", "show": "name"}])
    assert "rows" in str(_problem({"steps": [pick]}))
    defined = {"inputs": [{"name": "rows", "type": "text"}], "steps": [pick]}
    assert _problem(defined) is None
    without = _ask(message="Which?", fields=[{"name": "rows", "type": "pick"}])
    assert _problem({"steps": [without]}) is not None


@pytest.mark.parametrize(
    ("wait", "problem"),
    [
        ({"until": "duration"}, "takes `minutes`"),
        ({"until": "duration", "minutes": 5, "at": "09:00"}, "nothing else"),
        ({"until": "time", "at": "25:00"}, "isn't a time"),
        ({"until": "duration", "minutes": 5, "on": "today"}, "only waiting for a time"),
        ({"until": "duration", "minutes": 5, "save_as": "x"}, "only waiting for a file"),
        ({"until": "file", "path": "{{nowhere}}/in.csv"}, "nowhere"),
    ],
)
def test_a_wait_step_says_how_long_in_one_way(wait: dict[str, Any], problem: str) -> None:
    step = {"id": "w", "kind": "wait", "title": "Wait", **wait}
    assert problem in str(_problem({"steps": [step]}))


def test_steps_after_a_failure_never_pause() -> None:
    wait = {"id": "w", "kind": "wait", "title": "Wait", "until": "duration", "minutes": 5}
    assert _problem({"steps": [_write("x")], "after_failure": [wait]}) is not None
    assert _problem({"steps": [_write("x")], "after_failure": [_ask()]}) is not None


def test_later_steps_read_what_an_ask_or_a_wait_saved() -> None:
    wait = {"id": "w", "kind": "wait", "title": "Wait", "until": "file", "path": "in.csv",
            "save_as": "came"}  # fmt: skip
    steps = [_ask(), wait, _write("{{got.amount}} {{came.found}}")]
    assert _problem({"inputs": [{"name": "who"}], "steps": steps}) is None
    wrong = [_ask(), _write("{{got.total}}")]
    assert _problem({"inputs": [{"name": "who"}], "steps": wrong}) is not None


# -- an ask step --


async def test_an_ask_step_waits_for_its_values_and_later_steps_read_them(
    tmp_path: Path, clock: list[datetime]
) -> None:
    r = Run(tmp_path, [_ask(), _write("{{got.amount}}")], inputs=[{"name": "who"}])
    paused = await r.run.start({"who": "Lee"})
    assert paused.status == "waiting" and paused.step_id == "ask"
    assert paused.request["message"] == "How much for Lee?"
    pause = paused.request["pause"]
    assert pause["kind"] == "ask" and pause["until"] is None
    assert [f["name"] for f in pause["fields"]] == ["amount", "note"]
    assert paused_at([r.records[-1].to_dict()]) == pause

    done = await r.run.answer(True, "", {"amount": "12.5"})

    assert done.status == "completed"
    assert done.values["got"] == {"amount": 12.5, "note": ""}
    assert r.written == [12.5]
    assert r.statuses() == [("ask", "waiting"), ("ask", "done"), ("write", "done")]


async def test_an_answer_that_doesnt_fit_is_asked_for_again_saying_why(
    tmp_path: Path, clock: list[datetime]
) -> None:
    r = Run(tmp_path, [_ask(), _write("{{got.amount}}")], inputs=[{"name": "who"}])
    await r.run.start({"who": "Lee"})
    again = await r.run.answer(True, "", {"amount": "lots"})
    assert again.status == "waiting" and again.step_id == "ask"
    assert r.records[-1].status == "waiting" and "number" in (r.records[-1].error or "")
    done = await r.run.answer(True, "", {"amount": 3})
    assert done.status == "completed" and r.written == [3]


async def test_stopping_at_an_ask_step_fails_the_run_as_declined(
    tmp_path: Path, clock: list[datetime]
) -> None:
    r = Run(tmp_path, [_ask(), _write("x")], inputs=[{"name": "who"}])
    await r.run.start({"who": "Lee"})
    stopped = await r.run.answer(False)
    assert stopped.status == "failed" and stopped.step_id == "ask"
    assert r.written == []


async def test_a_pick_holds_the_items_the_person_ticked(
    tmp_path: Path, clock: list[datetime]
) -> None:
    pick = _ask(message="Which?", fields=[{"name": "rows", "type": "pick", "items": "rows",
                                           "show": "name"}])  # fmt: skip
    rows = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
    r = Run(tmp_path, [pick], inputs=[{"name": "rows"}])
    paused = await r.run.start({"rows": rows})
    [field] = paused.request["pause"]["fields"]
    assert field["items"] == [{"label": n, "index": i} for i, n in enumerate("abc")]
    wrong = await r.run.answer(True, "", {"rows": [7]})
    assert wrong.status == "waiting"
    done = await r.run.answer(True, "", {"rows": [2, 0]})
    assert done.values["got"] == {"rows": [{"name": "a"}, {"name": "c"}]}


async def test_no_answer_in_time_fails_or_goes_on_with_the_defaults(
    tmp_path: Path, clock: list[datetime]
) -> None:
    timed = _ask(timeout_hours=2, fields=[{"name": "amount", "type": "number", "default": 5}])
    failing = Run(tmp_path, [timed, _write("x")], inputs=[{"name": "who"}])
    paused = await failing.run.start({"who": "Lee"})
    assert paused.request["pause"]["until"] == "2026-11-02T11:00:00"
    assert (await failing.run.wake()).status == "waiting"  # woken early: still asking
    clock[0] += timedelta(hours=3)
    failed = await failing.run.wake()
    assert failed.status == "failed" and failing.written == []

    clock[0] = NOW
    going = Run(tmp_path, [{**timed, "on_timeout": "defaults"}, _write("{{got.amount}}")],
                inputs=[{"name": "who"}])  # fmt: skip
    await going.run.start({"who": "Lee"})
    clock[0] += timedelta(hours=3)
    done = await going.run.wake()
    assert done.status == "completed" and going.written == [5]
    report = run_report(going.workflow, [rec.to_dict() for rec in going.records])
    assert [u["step_id"] for u in report["unanswered"]] == ["ask"]


def test_answers_are_checked_before_the_run_goes_on() -> None:
    step = parse_workflow({"inputs": [{"name": "who"}], "steps": [_ask()]}).steps[0]
    assert answer_problem(step, {"amount": ""}) == "Amount needs a value"
    assert "number" in str(answer_problem(step, {"amount": "lots"}))
    assert answer_problem(step, {"amount": 4}) is None


# -- a wait step --


async def test_a_wait_holds_the_run_until_its_time_or_until_told_to_go_on(
    tmp_path: Path, clock: list[datetime]
) -> None:
    wait = {"id": "w", "kind": "wait", "title": "Wait", "until": "duration", "minutes": 30}
    r = Run(tmp_path, [wait, _write("after")])
    paused = await r.run.start({})
    pause = paused.request["pause"]
    assert paused.status == "waiting" and pause == {"kind": "wait", "until": "2026-11-02T09:30:00"}
    assert not wake_due(pause, NOW + timedelta(minutes=29))
    assert (await r.run.wake()).status == "waiting"
    clock[0] += timedelta(minutes=31)
    assert wake_due(pause, clock[0])
    assert (await r.run.wake()).status == "completed" and r.written == ["after"]

    early = Run(tmp_path, [wait, _write("early")])
    await early.run.start({})
    assert (await early.run.answer(True)).status == "completed" and early.written == ["early"]


async def test_a_wait_for_a_time_waits_for_the_next_one_or_the_day_named(
    tmp_path: Path, clock: list[datetime]
) -> None:
    at = {"id": "w", "kind": "wait", "title": "Wait", "until": "time", "at": "08:00"}
    tomorrow = await Run(tmp_path, [at]).run.start({})
    assert tomorrow.request["pause"]["until"] == "2026-11-03T08:00:00"
    later = await Run(tmp_path, [{**at, "at": "17:00"}]).run.start({})
    assert later.request["pause"]["until"] == "2026-11-02T17:00:00"
    named = Run(tmp_path, [{**at, "on": "due"}], inputs=[{"name": "due", "type": "date"}])
    assert (await named.run.start({"due": "2026-11-20"})).request["pause"]["until"] == (
        "2026-11-20T08:00:00"
    )


async def test_a_wait_for_a_file_goes_on_once_it_has_stopped_changing(
    tmp_path: Path, clock: list[datetime]
) -> None:
    wait = {"id": "w", "kind": "wait", "title": "Wait", "until": "file",
            "path": "in/{{name}}.csv", "save_as": "came", "max_minutes": 60}  # fmt: skip
    r = Run(tmp_path, [wait, _write("{{came.found}}")], inputs=[{"name": "name"}])
    paused = await r.run.start({"name": "May"})
    target = tmp_path / "in" / "May.csv"
    assert paused.request["pause"]["path"] == str(target)
    target.parent.mkdir()
    target.write_text("half", encoding="utf-8")  # still being written
    assert not wake_due(paused.request["pause"], clock[0])
    assert (await r.run.wake()).status == "waiting"
    _settled(target)
    assert wake_due(paused.request["pause"], clock[0])
    done = await r.run.wake()
    assert done.status == "completed"
    assert done.values["came"] == {"path": str(target), "found": True}


async def test_a_file_that_never_comes_fails_the_step_or_goes_on_without_it(
    tmp_path: Path, clock: list[datetime]
) -> None:
    wait = {"id": "w", "kind": "wait", "title": "Wait", "until": "file", "path": "none.csv",
            "save_as": "came", "max_minutes": 60}  # fmt: skip
    failing = Run(tmp_path, [wait, _write("x")])
    await failing.run.start({})
    clock[0] += timedelta(minutes=61)
    assert (await failing.run.wake()).status == "failed" and failing.written == []

    clock[0] = NOW
    going = Run(tmp_path, [{**wait, "if_missing": "continue"}, _write("{{came.found}}")])
    await going.run.start({})
    clock[0] += timedelta(minutes=61)
    assert (await going.run.wake()).status == "completed" and going.written == [False]


async def test_a_loop_can_skip_an_item_whose_file_never_came(
    tmp_path: Path, clock: list[datetime]
) -> None:
    _settled(tmp_path / "a.csv")
    loop = {"id": "each", "kind": "loop", "title": "Each", "over": "names", "item": "name",
            "on_item_failure": "skip", "collect": "came", "save_as": "all",
            "steps": [{"id": "w", "kind": "wait", "title": "Wait", "until": "file",
                       "path": "{{name}}.csv", "save_as": "came", "max_minutes": 1}]}  # fmt: skip
    r = Run(tmp_path, [loop], inputs=[{"name": "names"}])
    paused = await r.run.start({"names": ["a", "b"]})
    assert paused.status == "waiting"
    clock[0] += timedelta(minutes=2)
    done = await r.run.wake()
    assert done.status == "completed"
    assert done.values["all"] == [{"path": str(tmp_path / "a.csv"), "found": True}]


# -- a test run --


async def test_a_test_run_doesnt_wait_and_answers_with_the_defaults(
    tmp_path: Path, clock: list[datetime]
) -> None:
    wait = {"id": "w", "kind": "wait", "title": "Wait", "until": "duration", "minutes": 600}
    ask = _ask(fields=[{"name": "amount", "type": "number", "default": 2}])
    r = Run(tmp_path, [wait, ask, _write("{{got.amount}}")], inputs=[{"name": "who"}])
    result = await run_test(r.workflow, r.ctx, {"who": "Lee"})
    assert result["status"] == "passed" and r.written == [2]

    asks = Run(tmp_path, [_ask(), _write("x")], inputs=[{"name": "who"}])
    stopped = await run_test(asks.workflow, asks.ctx, {"who": "Lee"})
    assert stopped["status"] == "stopped_at_approval" and asks.written == []
