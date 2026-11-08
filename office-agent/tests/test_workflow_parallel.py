"""A step that runs its lanes at the same time (decision 0036): what saving one checks, the
lanes really overlapping, their results read after the step, their pauses answered one at a
time, a failed lane failing the step after the others end, and a retry going on only in the
lanes that failed."""

import asyncio
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from coscribe.workflow_spec import parse_workflow, task_results
from coscribe.workflows import StepContext, StepRecord, WorkflowRun, run_report, run_test


def _note(step_id: str, text: str, save_as: str | None = None, **extra: Any) -> dict[str, Any]:
    step = {"id": step_id, "title": step_id, "kind": "tool", "tool": "note", "args": {"text": text}}
    return {**step, **({"save_as": save_as} if save_as else {}), **extra}


def _slow(step_id: str, text: str, save_as: str | None = None) -> dict[str, Any]:
    return {**_note(step_id, text, save_as), "tool": "slow"}


def _approval(step_id: str) -> dict[str, Any]:
    return {"id": step_id, "title": step_id, "kind": "approval", "message": f"ok {step_id}?"}


def _parallel(*lanes: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    named = [{"label": f"Lane {n + 1}", "steps": steps} for n, steps in enumerate(lanes)]
    return {"id": "both", "title": "Both at once", "kind": "parallel", "lanes": named, **extra}


class World:
    def __init__(self, tmp_path: Path) -> None:
        self.written: list[Any] = []
        self.failures = 0
        self.running = 0
        self.most = 0
        self.records: list[StepRecord] = []
        self.saver = InMemorySaver()
        self.ctx = StepContext(
            tools={"note": self.note, "slow": self.slow, "flaky": self.flaky},
            workspace_root=tmp_path,
            state_dir=tmp_path / "state",
            make_model=lambda name: None,
        )

    def note(self, text: Any) -> dict[str, Any]:
        self.written.append(text)
        return {"text": text}

    async def slow(self, text: Any) -> dict[str, Any]:
        self.running += 1
        self.most = max(self.most, self.running)
        await asyncio.sleep(0.05)
        self.running -= 1
        return self.note(text)

    def flaky(self, text: Any) -> dict[str, Any]:
        if self.failures:
            self.failures -= 1
            raise RuntimeError("the site didn't answer")
        return self.note(text)

    def run(self, data: dict[str, Any], thread: str = "run-1") -> WorkflowRun:
        return WorkflowRun(parse_workflow(data), self.ctx, self.saver, thread, self.records.append)

    def done(self, step_id: str) -> int:
        return sum(1 for r in self.records if r.step_id == step_id and r.status == "done")


# -- saving -----------------------------------------------------------------


def test_lanes_read_only_what_came_before_and_save_different_names() -> None:
    lanes = _parallel([_note("a", "x", "first")], [_note("b", "y", "second")])
    workflow = parse_workflow({"version": 1, "steps": [lanes, _note("c", "{{first.text}}")]})
    assert task_results(workflow) == {"first": None, "second": None}
    with pytest.raises(ValidationError, match="reads 'first'"):
        parse_workflow({"version": 1, "steps": [
            _parallel([_note("a", "x", "first")], [_note("b", "{{first}}")])]})  # fmt: skip
    with pytest.raises(ValidationError, match="already taken"):
        parse_workflow({"version": 1, "steps": [
            _parallel([_note("a", "x", "same")], [_note("b", "y", "same")])]})  # fmt: skip
    with pytest.raises(ValidationError, match="different name"):
        parse_workflow({"version": 1, "steps": [{**lanes, "lanes": [
            {"label": "Mail", "steps": []}, {"label": " mail ", "steps": []}]}]})  # fmt: skip
    with pytest.raises(ValidationError, match="at least 2"):
        parse_workflow({"version": 1, "steps": [{**lanes, "lanes": lanes["lanes"][:1]}]})


# -- running ----------------------------------------------------------------


async def test_lanes_run_at_the_same_time_and_their_results_are_read_after(
    tmp_path: Path,
) -> None:
    world = World(tmp_path)
    steps = [
        _note("start", "s", "before"),
        _parallel([_slow("a", "{{before.text}}-a", "first")], [_slow("b", "b", "second")],
                  [_slow("c", "c")]),
        _note("after", "{{first.text}} {{second.text}}"),
    ]  # fmt: skip
    outcome = await world.run({"version": 1, "steps": steps}).start({})
    assert outcome.status == "completed", outcome.error
    assert world.most == 3
    assert world.written[-1] == "s-a b"
    assert [world.done(i) for i in ("a", "b", "c", "both", "after")] == [1, 1, 1, 1, 1]
    report = run_report(parse_workflow({"version": 1, "steps": steps}),
                        [r.to_dict() for r in world.records])  # fmt: skip
    assert report["not_done"] == []


async def test_pauses_in_lanes_are_answered_one_at_a_time(tmp_path: Path) -> None:
    world = World(tmp_path)
    steps = [_parallel([_approval("left"), _note("l", "l")], [_approval("right"),
                                                               _note("r", "r")]),
             _note("end", "e")]  # fmt: skip
    run = world.run({"version": 1, "steps": steps})
    outcome = await run.start({})
    assert (outcome.status, outcome.step_id) == ("waiting", "left")
    outcome = await run.answer(True)
    assert (outcome.status, outcome.step_id) == ("waiting", "right")
    outcome = await run.answer(True)
    assert outcome.status == "completed", outcome.error
    assert sorted(world.written[:2]) == ["l", "r"] and world.written[2] == "e"


async def test_no_in_one_lane_fails_the_step_after_the_other_ends(tmp_path: Path) -> None:
    world = World(tmp_path)
    run = world.run({"version": 1, "steps": [
        _parallel([_approval("ask")], [_slow("other", "o")])]})  # fmt: skip
    await run.start({})
    assert world.written == ["o"]
    outcome = await run.answer(False, "not this time")
    assert outcome.status == "failed" and outcome.declined
    assert "Lane 1: Not approved: not this time" in (outcome.error or "")
    # Going on asks again in that lane, and the lane that ended isn't run again.
    outcome = await run.resume()
    assert (outcome.status, outcome.step_id) == ("waiting", "ask"), outcome.error
    outcome = await run.answer(True)
    assert outcome.status == "completed", outcome.error
    assert world.written == ["o"]


async def test_a_retry_goes_on_only_in_the_lane_that_failed(tmp_path: Path) -> None:
    world = World(tmp_path)
    shaky = {**_note("shaky", "2"), "tool": "flaky"}
    retry = {"on_failure": {"retries": 1, "wait_seconds": 0}}
    world.failures = 1
    outcome = await world.run({"version": 1, "steps": [
        _parallel([_note("once", "1")], [shaky], **retry)]}).start({})  # fmt: skip
    assert outcome.status == "completed", outcome.error
    assert sorted(world.written) == ["1", "2"]
    assert world.done("once") == 1


async def test_a_failed_lane_can_be_skipped_and_resumed_later(tmp_path: Path) -> None:
    world = World(tmp_path)
    shaky = {**_note("shaky", "2"), "tool": "flaky"}
    world.failures = 1
    run = world.run({"version": 1, "steps": [_parallel([_note("once", "1")], [shaky])]})
    outcome = await run.start({})
    assert outcome.status == "failed"
    assert "Lane 2: " in (outcome.error or "") and "didn't answer" in (outcome.error or "")
    # The report names the lane's step, not the parallel step around it as well.
    workflow = parse_workflow({"version": 1, "steps": [_parallel([_note("once", "1")], [shaky])]})
    report = run_report(workflow, [r.to_dict() for r in world.records])
    assert [entry["step_id"] for entry in report["not_done"]] == ["shaky"]
    outcome = await run.resume()
    assert outcome.status == "completed", outcome.error
    assert world.done("once") == 1 and world.done("shaky") == 1


async def test_a_parallel_step_inside_a_loop_runs_its_lanes_per_item(tmp_path: Path) -> None:
    world = World(tmp_path)
    loop = {"id": "each", "title": "each", "kind": "loop", "over": "items", "item": "it",
            "steps": [_parallel([_note("a", "a{{it}}", "x")], [_note("b", "b{{it}}")])],
            "collect": "x.text", "save_as": "all"}  # fmt: skip
    run = world.run({"version": 1, "inputs": [{"name": "items", "type": "text"}], "steps": [loop]})
    outcome = await run.start({"items": ["1", "2"]})
    assert outcome.status == "completed", outcome.error
    assert outcome.values["all"] == ["a1", "a2"]
    assert sorted((r.step_id, tuple(r.iteration)) for r in world.records
                  if r.status == "done" and r.step_id in ("a", "b")) == [
        ("a", (0,)), ("a", (1,)), ("b", (0,)), ("b", (1,))]  # fmt: skip


async def test_a_test_run_stops_before_a_lane_step_that_cant_be_undone(tmp_path: Path) -> None:
    world = World(tmp_path)
    workflow = parse_workflow({"version": 1, "steps": [
        _parallel([_note("draft", "d")], [_note("send", "s", irreversible=True)])]})  # fmt: skip
    result = await run_test(workflow, world.ctx)
    assert result["status"] == "stopped_before_irreversible"
    assert result["stopped_before"]["id"] == "send"
    assert "s" not in world.written
