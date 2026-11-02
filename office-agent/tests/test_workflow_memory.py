"""A task that remembers between runs, and ends quietly when there is nothing to do (decision
0034): the spec's rules, the engine, the memory store, the run report and the test run."""

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from coscribe.tools import TaskMemory
from coscribe.workflow_spec import memory_value, parse_workflow
from coscribe.workflow_spec.inputs import MAX_MEMORY_CHARS
from coscribe.workflows import StepContext, StepRecord, WorkflowRun, run_report, run_test

MEMORY = [
    {"name": "seen", "label": "Already handled", "type": "list", "initial": []},
    {"name": "last", "type": "text"},
]


def _workflow(steps: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"version": 1, "memory": MEMORY, "steps": steps, **extra}


def _note(step_id: str, text: str, save_as: str | None = None) -> dict[str, Any]:
    step = {"id": step_id, "title": step_id, "kind": "tool", "tool": "note", "args": {"text": text}}
    return {**step, "save_as": save_as} if save_as else step


def _remember(step_id: str, name: str, value: str) -> dict[str, Any]:
    return {"id": step_id, "title": step_id, "kind": "remember", "name": name, "value": value}


def _end_unless(step_id: str, ref: str) -> dict[str, Any]:
    return {"id": step_id, "title": step_id, "kind": "check", "otherwise": "end",
            "conditions": [{"left": {"ref": ref}, "op": "not_empty"}]}  # fmt: skip


class Notes:
    def __init__(self, tmp_path: Path) -> None:
        self.written: list[Any] = []
        self.records: list[StepRecord] = []
        self.ctx = StepContext(
            tools={"note": self.note},
            workspace_root=tmp_path,
            state_dir=tmp_path / "state",
            make_model=lambda name: None,
        )

    def note(self, text: Any) -> dict[str, Any]:
        self.written.append(text)
        return {"text": text, "items": ["b", "c"]}

    def on_step(self, record: StepRecord) -> None:
        self.records.append(record)

    def run(self, data: dict[str, Any]) -> WorkflowRun:
        return WorkflowRun(parse_workflow(data), self.ctx, InMemorySaver(), "run-1", self.on_step)


# -- the spec ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (_workflow([_remember("r", "unknown", "x")]), "doesn't keep"),
        ({"version": 1, "steps": [_remember("r", "seen", "x")]}, "doesn't keep"),
        (_workflow([_note("a", "{{memory.nope}}")]), "memory only has"),
        (_workflow([_note("a", "{{run.week}}")]), "run only has"),
        (
            _workflow([_note("a", "x")], inputs=[{"name": "memory", "type": "text"}]),
            "rename that input",
        ),
        (
            {"version": 1, "memory": [MEMORY[0], MEMORY[0]], "steps": [_note("a", "x")]},
            "its own name",
        ),
        (
            _workflow(
                [
                    {
                        "id": "l",
                        "title": "l",
                        "kind": "loop",
                        "over": "memory.seen",
                        "item": "x",
                        "steps": [_end_unless("c", "x")],
                    }
                ]
            ),
            "only a check outside loops",
        ),
        (
            {
                "version": 1,
                "memory": [{"name": "n", "type": "number", "initial": "ten"}],
                "steps": [_note("a", "x")],
            },
            "needs a number",
        ),
    ],
)
def test_the_spec_refuses_memory_it_cant_keep(data: dict[str, Any], problem: str) -> None:
    with pytest.raises(ValidationError, match=problem):
        parse_workflow(data)


def test_run_is_only_a_name_where_the_task_remembers() -> None:
    parse_workflow({"version": 1, "inputs": [{"name": "run", "type": "text", "default": "x"}],
                    "steps": [_note("a", "{{run}}")]})  # fmt: skip


def test_a_list_too_big_keeps_its_newest_items() -> None:
    items = [f"id-{i:06d}" for i in range(5000)]
    kept = memory_value("seen", "list", items)
    assert kept[-1] == "id-004999" and len(json.dumps(kept)) <= MAX_MEMORY_CHARS
    assert kept == items[-len(kept) :]
    with pytest.raises(ValueError, match="over"):
        memory_value("last", "text", "x" * (MAX_MEMORY_CHARS + 1))
    assert memory_value("when", "date", "2026-11-02T09:30:00") == "2026-11-02T09:30:00"
    with pytest.raises(ValueError, match="date"):
        memory_value("when", "date", "yesterday")
    assert memory_value("n", "number", "3") == 3
    assert memory_value("last", "text", {"a": 1}) == '{"a": 1}'


# -- the engine -------------------------------------------------------------


async def test_a_run_reads_its_memory_and_keeps_new_values_only_in_its_outcome(
    tmp_path: Path,
) -> None:
    notes = Notes(tmp_path)
    data = _workflow([
        _note("read", "{{memory.seen}}", "found"),
        _remember("keep", "seen", "{{found.items}}"),
        _note("again", "{{memory.seen}}"),
        _remember("stamp", "last", "checked {{run.date}}"),
    ])  # fmt: skip

    outcome = await notes.run(data).start({}, {"seen": ["a"]})

    assert outcome.status == "completed" and not outcome.ended
    # A later step of the same run still reads the old value.
    assert notes.written == [["a"], ["a"]]
    assert outcome.remembered["seen"] == ["b", "c"]
    assert outcome.remembered["last"].startswith("checked 20")


async def test_the_first_run_reads_each_values_starting_value(tmp_path: Path) -> None:
    notes = Notes(tmp_path)
    outcome = await notes.run(_workflow([_note("read", "{{memory.seen}}|{{memory.last}}")])).start(
        {}
    )
    assert outcome.status == "completed"
    assert notes.written == ["|"]


async def test_a_check_that_ends_the_run_leaves_the_rest_and_counts_as_done(
    tmp_path: Path,
) -> None:
    notes = Notes(tmp_path)
    data = _workflow([
        _remember("stamp", "last", "{{run.started_at}}"),
        _end_unless("anything", "memory.seen"),
        _note("work", "should not run"),
    ])  # fmt: skip

    outcome = await notes.run(data).start({}, {"seen": []})

    assert outcome.status == "completed" and outcome.ended
    assert notes.written == []
    # What came before the check is still kept.
    assert set(outcome.remembered) == {"last"}
    ended = next(r for r in notes.records if r.step_id == "anything")
    assert ended.status == "done" and ended.note and "Nothing to do" in ended.note
    report = run_report(parse_workflow(data), [r.to_dict() for r in notes.records])
    assert report["ended"] == {"step_id": "anything", "title": "anything"}
    assert report["remembered"][0]["name"] == "last"


async def test_a_value_that_isnt_the_memorys_type_fails_the_step(tmp_path: Path) -> None:
    notes = Notes(tmp_path)
    data = _workflow([_note("read", "x", "found"), _remember("keep", "seen", "{{found.text}}")])
    outcome = await notes.run(data).start({})
    assert outcome.status == "failed" and outcome.step_id == "keep"
    assert "keeps a list" in (outcome.error or "")


async def test_a_test_run_reads_memory_and_says_what_it_would_keep(tmp_path: Path) -> None:
    notes = Notes(tmp_path)
    data = _workflow([_note("read", "{{memory.seen}}", "found"),
                      _remember("keep", "seen", "{{found.items}}")])  # fmt: skip
    result = await run_test(parse_workflow(data), notes.ctx, {}, None, "t", memory={"seen": ["z"]})
    assert result["status"] == "passed"
    assert result["would_remember"] == {"seen": json.dumps(["b", "c"])}
    assert notes.written == [["z"]]

    quiet = await run_test(
        parse_workflow(_workflow([_end_unless("c", "memory.seen"), _note("w", "x")])),
        notes.ctx, {}, None, "t",
    )  # fmt: skip
    assert quiet["status"] == "passed" and quiet["ended"] is True
    assert [s["status"] for s in quiet["steps"]] == ["done", "not reached"]


# -- the store --------------------------------------------------------------


def test_task_memory_keeps_runs_values_and_a_persons_edits(tmp_path: Path) -> None:
    memory = TaskMemory(tmp_path)
    declared = parse_workflow(_workflow([_note("a", "x")])).memory
    assert memory.values("t1") == {}
    memory.keep("t1", {"seen": ["a"]}, "run1")
    memory.keep("t1", {}, "run2")
    assert memory.entries("t1")["seen"]["by"] == "run1"

    memory.set("t1", declared, "last", "by hand")
    assert memory.values("t1") == {"seen": ["a"], "last": "by hand"}
    assert memory.entries("t1")["last"]["by"] == "you"
    with pytest.raises(ValueError, match="keeps a list"):
        memory.set("t1", declared, "seen", "not a list")
    with pytest.raises(KeyError):
        memory.set("t1", declared, "other", "x")
    # Blank forgets it: the next run reads the starting value.
    memory.set("t1", declared, "seen", None)
    assert memory.values("t1") == {"last": "by hand"}

    memory.delete("t1")
    assert memory.values("t1") == {}
