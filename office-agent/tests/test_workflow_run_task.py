"""A task that runs another as a step, and the versions a task keeps (decision 0035): the
checks saving one makes, the engine passing the called run's pauses, failures and results
through, the version history, and a test run."""

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from coscribe.tools.bookkeeping.scheduled_tasks import (
    ScheduledTriggerStore,
    create_trigger,
    patch_trigger,
    update_trigger,
)
from coscribe.workflow_spec import parse_workflow, task_results
from coscribe.workflows import (
    StepContext,
    StepRecord,
    TaskSource,
    WorkflowRun,
    pause_steps,
    run_test,
)


def _note(step_id: str, text: str, save_as: str | None = None, **extra: Any) -> dict[str, Any]:
    step = {"id": step_id, "title": step_id, "kind": "tool", "tool": "note", "args": {"text": text}}
    return {**step, **({"save_as": save_as} if save_as else {}), **extra}


def _approval(step_id: str) -> dict[str, Any]:
    return {"id": step_id, "title": step_id, "kind": "approval", "message": f"ok {step_id}?"}


def _call(task: str, save_as: str | None = "got", **extra: Any) -> dict[str, Any]:
    step = {"id": "call", "title": "Run the other", "kind": "run_task", "task": task}
    return {**step, **({"save_as": save_as} if save_as else {}), **extra}


def _save(store: ScheduledTriggerStore, name: str, workflow: dict[str, Any]) -> str:
    trigger = create_trigger(store, name=name, kind="manual", at="", prompt="", workflow=workflow)
    return trigger.trigger_id


CALLED = {
    "version": 1,
    "inputs": [
        {"name": "month", "label": "Month", "type": "text"},
        {"name": "region", "type": "text", "default": "north"},
    ],  # fmt: skip
    "memory": [{"name": "last", "type": "text"}],
    "steps": [
        _note("fetch", "sales {{month}} {{region}}", "sales"),
        {"id": "keep", "title": "keep", "kind": "remember", "name": "last", "value": "{{month}}"},
    ],
}


class World:
    def __init__(self, tmp_path: Path) -> None:
        self.store = ScheduledTriggerStore(tmp_path / "state")
        self.written: list[Any] = []
        self.failures = 0
        self.records: list[StepRecord] = []
        self.called: dict[str, Any] = {}
        self.saver = InMemorySaver()
        self.ctx = StepContext(
            tools={"note": self.note, "flaky": self.flaky},
            workspace_root=tmp_path,
            state_dir=tmp_path / "state",
            make_model=lambda name: None,
            tasks=TaskSource(self.store, record=self.called.__setitem__, chain=("caller",)),
        )

    def note(self, text: Any) -> dict[str, Any]:
        self.written.append(text)
        return {"text": text}

    def flaky(self, text: Any) -> dict[str, Any]:
        if self.failures:
            self.failures -= 1
            raise RuntimeError("the site didn't answer")
        return self.note(text)

    def run(self, data: dict[str, Any], thread: str = "run-1") -> WorkflowRun:
        return WorkflowRun(parse_workflow(data), self.ctx, self.saver, thread, self.records.append)

    def ids(self, status: str) -> list[str]:
        return [r.step_id for r in self.records if r.status == status]


# -- saving -----------------------------------------------------------------


def test_the_spec_takes_a_run_task_step_and_says_what_a_task_gives() -> None:
    workflow = parse_workflow({"version": 1, "steps": [_call("abc", inputs={"month": "x"})]})
    assert workflow.steps[0].kind == "run_task"
    assert task_results(parse_workflow(CALLED)) == {"sales": None}
    with pytest.raises(ValidationError, match="lowercase letter"):
        parse_workflow({"version": 1, "steps": [_call("abc", inputs={"Month": "x"})]})


@pytest.mark.parametrize(
    ("step", "problem"),
    [
        (_call("nope"), "no longer exists"),
        (_call("{called}", inputs={"month": "5", "week": "1"}), "has no input 'week'"),
        (_call("{called}"), "needs a value for “Month”"),
        (_call("{called}", inputs={"month": "5"}), None),
    ],
)
def test_saving_checks_the_task_it_runs(
    tmp_path: Path, step: dict[str, Any], problem: str | None
) -> None:
    store = ScheduledTriggerStore(tmp_path)
    called = _save(store, "Fetch sales", CALLED)
    step = {**step, "task": step["task"].replace("{called}", called)}
    workflow = {"version": 1, "steps": [step, _note("use", "{{got.sales.text}}")]}
    if problem is None:
        _save(store, "Report", workflow)
        return
    with pytest.raises(ValueError, match=problem):
        _save(store, "Report", workflow)


def test_saving_checks_the_results_the_caller_reads(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path)
    called = _save(store, "Fetch sales", CALLED)
    workflow = {"version": 1, "steps": [_call(called, inputs={"month": "5"}),
                                         _note("use", "{{got.total}}")]}  # fmt: skip
    with pytest.raises(ValueError, match="“Fetch sales” gives sales"):
        _save(store, "Report", workflow)


def test_tasks_never_run_each_other_in_a_circle_or_too_deep(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path)
    leaf = _save(store, "D", {"version": 1, "steps": [_note("a", "x")]})
    ids = [leaf]
    for name in ("C", "B", "A"):
        ids.append(_save(store, name, {"version": 1, "steps": [_call(ids[-1], save_as=None)]}))
    with pytest.raises(ValueError, match="at most 3 deep"):
        _save(store, "Top", {"version": 1, "steps": [_call(ids[-1], save_as=None)]})
    # Making the bottom one run another makes the chain above it too deep as well.
    other = _save(store, "E", {"version": 1, "steps": [_note("a", "x")]})
    with pytest.raises(ValueError, match="at most 3 deep"):
        update_trigger(store, leaf, name="D", kind="manual", at="", prompt="",
                       workflow={"version": 1, "steps": [_call(other, save_as=None)]})  # fmt: skip
    with pytest.raises(ValueError, match="in a circle"):
        update_trigger(store, ids[1], name="C", kind="manual", at="", prompt="",
                       workflow={"version": 1, "steps": [_call(ids[3], save_as=None)]})  # fmt: skip
    with pytest.raises(ValueError, match="can't run itself"):
        update_trigger(store, leaf, name="D", kind="manual", at="", prompt="",
                       workflow={"version": 1, "steps": [_call(leaf, save_as=None)]})  # fmt: skip


# -- running ----------------------------------------------------------------


async def test_a_step_runs_another_task_and_reads_its_results(tmp_path: Path) -> None:
    world = World(tmp_path)
    called = _save(world.store, "Fetch sales", CALLED)
    outcome = await world.run(
        {"version": 1, "inputs": [{"name": "m", "type": "text", "default": "2026-10"}],
         "steps": [_call(called, inputs={"month": "{{m}}"}), _note("use", "{{got.sales.text}}")]}
    ).start({})  # fmt: skip
    assert outcome.status == "completed", outcome.error
    assert world.written == ["sales 2026-10 north", "sales 2026-10 north"]
    assert world.ids("done") == ["call/fetch", "call/keep", "call", "use"]
    # What it remembers is its own, kept once its part finished.
    assert world.store.memory.values(called) == {"last": "2026-10"}
    assert world.called["call"]["version"] == 1
    assert world.called["call"]["name"] == "Fetch sales"


async def test_the_called_tasks_pauses_pause_the_caller(tmp_path: Path) -> None:
    world = World(tmp_path)
    steps = [_approval("first"), _note("between", "b"), _approval("second"), _note("end", "e")]
    called = _save(world.store, "Two approvals", {"version": 1, "steps": steps})
    run = world.run({"version": 1, "steps": [_call(called, save_as=None), _note("after", "a")]})
    outcome = await run.start({})
    assert (outcome.status, outcome.step_id) == ("waiting", "call/first")
    assert outcome.request and outcome.request["task"] == "Two approvals"
    outcome = await run.answer(True)
    assert (outcome.status, outcome.step_id) == ("waiting", "call/second")
    outcome = await run.answer(True)
    assert outcome.status == "completed", outcome.error
    # Each step ran once, though the step running the task ran again on each answer.
    assert world.written == ["b", "e", "a"]


async def test_no_inside_the_called_task_stops_the_caller(tmp_path: Path) -> None:
    world = World(tmp_path)
    called = _save(world.store, "Asks", {"version": 1, "steps": [_approval("ok")]})
    run = world.run({"version": 1, "steps": [_call(called, save_as=None)]})
    await run.start({})
    outcome = await run.answer(False, "not now")
    assert outcome.status == "failed"
    assert outcome.declined
    assert "“Asks” stopped: Not approved: not now" in (outcome.error or "")


async def test_resuming_goes_on_from_where_the_called_task_failed(tmp_path: Path) -> None:
    world = World(tmp_path)
    steps = [_note("once", "1"), {**_note("shaky", "2"), "tool": "flaky"}]
    called = _save(world.store, "Shaky", {"version": 1, "steps": steps})
    run = world.run({"version": 1, "steps": [_call(called, save_as=None)]})
    world.failures = 1
    outcome = await run.start({})
    assert outcome.status == "failed"
    assert "the site didn't answer" in (outcome.error or "")
    outcome = await run.resume()
    assert outcome.status == "completed", outcome.error
    assert world.written == ["1", "2"]


async def test_a_retry_of_the_step_goes_on_inside_the_called_task(tmp_path: Path) -> None:
    world = World(tmp_path)
    steps = [_note("once", "1"), {**_note("shaky", "2"), "tool": "flaky"}]
    called = _save(world.store, "Shaky", {"version": 1, "steps": steps})
    retry = {"on_failure": {"retries": 2, "wait_seconds": 0}}
    world.failures = 2
    outcome = await world.run(
        {"version": 1, "steps": [_call(called, save_as=None, **retry)]}
    ).start({})
    assert outcome.status == "completed", outcome.error
    assert world.written == ["1", "2"]
    assert [r.attempts for r in world.records if r.step_id == "call" and r.status == "done"] == [3]


async def test_a_loop_runs_the_task_once_per_item_and_a_wait_inside_it_wakes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = World(tmp_path)
    wait = {"id": "pause", "title": "pause", "kind": "wait", "until": "duration", "minutes": 1}
    called = _save(world.store, "Per item", {"version": 1, "inputs": [{"name": "x", "type": "text"}],
                                             "steps": [wait, _note("n", "{{x}}", "out")]})  # fmt: skip
    loop = {"id": "each", "title": "each", "kind": "loop", "over": "items", "item": "it",
            "steps": [_call(called, inputs={"x": "{{it}}"})], "collect": "got.out.text",
            "save_as": "all"}  # fmt: skip
    run = world.run({"version": 1, "inputs": [{"name": "items", "type": "text"}], "steps": [loop]})
    outcome = await run.start({"items": ["a", "b"]})
    assert (outcome.status, outcome.step_id) == ("waiting", "call/pause")
    assert outcome.request and outcome.request["pause"]["kind"] == "wait"
    shift = [0]
    real = pause_steps.clock
    monkeypatch.setattr(pause_steps, "clock", lambda: real() + timedelta(days=shift[0]))
    for _item in ("a", "b"):
        shift[0] += 1
        outcome = await run.wake()
    assert outcome.status == "completed", outcome.error
    assert outcome.values["all"] == ["a", "b"]
    done = [(r.step_id, r.iteration) for r in world.records if r.status == "done"]
    assert ("call/n", [0]) in done and ("call/n", [1]) in done


async def test_a_run_refuses_a_task_already_running_above_it(tmp_path: Path) -> None:
    world = World(tmp_path)
    called = _save(world.store, "Loop back", {"version": 1, "steps": [_note("a", "x")]})
    world.ctx.tasks = TaskSource(world.store, chain=(called,))
    outcome = await world.run({"version": 1, "steps": [_call(called, save_as=None)]}).start({})
    assert outcome.status == "failed"
    assert "can't run in a circle" in (outcome.error or "")


async def test_a_test_run_stops_before_a_called_step_that_cant_be_undone(tmp_path: Path) -> None:
    world = World(tmp_path)
    steps = [_note("draft", "d"), _note("send", "s", irreversible=True)]
    called = _save(world.store, "Send", {"version": 1, "memory": [{"name": "n", "type": "text"}],
                                         "steps": [*steps, {"id": "k", "title": "k",
                                                            "kind": "remember", "name": "n",
                                                            "value": "x"}]})  # fmt: skip
    result = await run_test(parse_workflow({"version": 1, "steps": [_call(called, save_as=None)]}),
                            world.ctx)  # fmt: skip
    assert result["status"] == "stopped_before_irreversible"
    assert result["stopped_before"] == {"id": "call/send", "title": "send"}
    assert world.written == ["d"]
    passed = await run_test(parse_workflow({"version": 1, "steps": [_call(called, save_as=None)]}),
                            world.ctx, send_for_real=True)  # fmt: skip
    assert passed["status"] == "passed"
    # A test keeps nothing, for the called task either.
    assert world.store.memory.values(called) == {}


# -- versions ---------------------------------------------------------------


def test_every_save_that_changes_the_workflow_is_a_version(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path)
    first = {"version": 1, "steps": [_note("a", "x")]}
    second = {"version": 1, "steps": [_note("a", "y")]}
    task = _save(store, "T", first)
    assert store.versions.current(task) == 1
    update_trigger(store, task, name="Renamed", kind="manual", at="", prompt="", workflow=first)
    assert store.versions.current(task) == 1
    patch_trigger(store, task, {"workflow": second, "from_draft": "d1"})
    restored = patch_trigger(store, task, {"workflow": store.versions.get(task, 1)["workflow"]},
                             restored_from=1)  # fmt: skip
    versions = store.versions.all(task)
    assert [(v["number"], v["how"], v.get("from")) for v in versions] == [
        (1, "created", None),
        (2, "conversation", None),
        (3, "restored", 1),
    ]
    assert restored.workflow == versions[0]["workflow"]
    store.delete(task)
    assert store.versions.all(task) == []


def test_a_task_saved_before_versions_starts_its_history_when_it_changes(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path)
    task = _save(store, "Old", {"version": 1, "steps": [_note("a", "x")]})
    store.versions.delete(task)
    update_trigger(store, task, name="Old", kind="manual", at="", prompt="",
                   workflow={"version": 1, "steps": [_note("a", "y")]})  # fmt: skip
    assert [v["how"] for v in store.versions.all(task)] == ["found", "edited"]
