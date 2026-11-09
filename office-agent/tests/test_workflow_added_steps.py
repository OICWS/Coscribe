"""Steps a run adds when a step fails (decision 0042)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver

from coscribe.workflow_spec import failure_policy, parse_workflow
from coscribe.workflows import StepContext, StepRecord, WorkflowRun, added_fix, run_report

EXPORT = "https://rates.example/export"


def _download(url: str = "") -> Any:
    raise RuntimeError("404: the export moved")


class Harness:
    def __init__(self, tmp_path: Path, replies: list[str]) -> None:
        self.records: list[StepRecord] = []
        self.planned = 0
        self.written: list[dict[str, Any]] = []
        self.replies = replies

        def write_file(path: str = "", content: str = "") -> dict[str, Any]:
            self.written.append({"path": path, "content": content})
            return {"path": path}

        def make_model(name: str | None) -> Any:
            self.planned += 1
            return FakeListChatModel(responses=self.replies)

        self.ctx = StepContext(
            tools={
                "download_rates": _download,
                "read_file": lambda path="": f"rates from {path}",
                "write_file": write_file,
            },
            workspace_root=tmp_path,
            state_dir=tmp_path / "state",
            make_model=make_model,
            read_tools=frozenset({"read_file"}),
            adds_steps=True,
        )

    def on_step(self, record: StepRecord) -> None:
        self.records.append(record)

    def run(self, autonomy: str = "proactive") -> WorkflowRun:
        workflow = parse_workflow({"version": 2, "autonomy": autonomy, "steps": STEPS})
        self.workflow = workflow
        return WorkflowRun(workflow, self.ctx, InMemorySaver(), "run-1", self.on_step)


STEPS = [
    {"id": "fetch", "kind": "tool", "title": "Download the rates", "tool": "download_rates",
     "args": {"url": EXPORT}, "save_as": "rates"},
    {"id": "save", "kind": "tool", "title": "Save the rates", "tool": "write_file",
     "args": {"path": "rates.txt", "content": "{{rates}}"}},
]  # fmt: skip


def _plan(*steps: dict[str, Any]) -> str:
    return json.dumps({"why": "The export moved; read the copy saved last time.", "steps": steps})


READ_SAVED = {"id": "read_saved", "kind": "tool", "title": "Read the saved rates",
              "tool": "read_file", "args": {"path": "rates.txt"}, "save_as": "rates"}  # fmt: skip


async def test_a_step_that_fails_at_proactive_gets_steps_that_stand_in_for_it(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path, [_plan(READ_SAVED)])

    outcome = await h.run().start({})

    assert outcome.status == "completed"
    assert h.written == [{"path": "rates.txt", "content": "rates from rates.txt"}]
    failed = next(r for r in h.records if r.step_id == "fetch" and r.status == "failed")
    assert failed.recovered == "added"
    assert failed.agent is not None and failed.agent["added"]["steps"][0]["id"] == "read_saved"
    assert any(r.step_id == "fetch/added/read_saved" and r.status == "done" for r in h.records)


async def test_a_fixed_task_stops_with_the_steps_own_error(tmp_path: Path) -> None:
    h = Harness(tmp_path, [_plan(READ_SAVED)])

    outcome = await h.run(autonomy="self_healing").start({})

    assert outcome.status == "failed"
    assert outcome.error == "404: the export moved"
    assert h.planned == 0


async def test_an_added_step_that_writes_waits_for_a_person_and_is_planned_once(
    tmp_path: Path,
) -> None:
    write = {"id": "note", "kind": "tool", "title": "Write a note", "tool": "write_file",
             "args": {"path": "rates.txt", "content": "{{failure.message}}"}}  # fmt: skip
    h = Harness(tmp_path, [_plan(write, READ_SAVED)])
    run = h.run()

    waiting = await run.start({})

    assert waiting.status == "waiting"
    assert waiting.step_id == "fetch/added/before_note"
    assert h.written == []
    done = await run.answer(True)
    assert done.status == "completed"
    assert h.written[0] == {"path": "rates.txt", "content": "404: the export moved"}
    assert h.planned == 1


async def test_a_value_taken_from_outside_is_refused(tmp_path: Path) -> None:
    leak = {**READ_SAVED, "args": {"path": "C:/Users/me/secrets.txt"}}
    h = Harness(tmp_path, [_plan(leak)])

    outcome = await h.run().start({})

    assert outcome.status == "failed"
    assert outcome.error is not None
    assert outcome.error.startswith("404: the export moved -- adding steps for it didn't work")
    assert "secrets.txt" in outcome.error
    assert h.written == []


async def test_a_script_is_never_added(tmp_path: Path) -> None:
    script = {"id": "convert", "kind": "script", "title": "Convert", "code": "print(1)",
              "save_as": "rates"}  # fmt: skip
    h = Harness(tmp_path, [_plan(script)])

    outcome = await h.run().start({})

    assert outcome.status == "failed"
    assert outcome.error is not None and "only tool, llm and check steps" in outcome.error


async def test_the_report_lists_the_added_steps_and_the_run_offers_them_as_a_fallback(
    tmp_path: Path,
) -> None:
    h = Harness(tmp_path, [_plan(READ_SAVED)])
    await h.run().start({})
    records = [r.to_dict() for r in h.records]

    report = run_report(h.workflow, records)
    fix = added_fix(h.workflow.model_dump(mode="json"), report["added"])

    assert report["added"][0]["step_id"] == "fetch"
    assert fix["steps"] == [{"step_id": "fetch", "title": "Download the rates",
                             "why": "The export moved; read the copy saved last time.",
                             "added": ["Read the saved rates"]}]  # fmt: skip
    saved = parse_workflow(fix["workflow"])
    policy = failure_policy(saved.steps[0])
    assert policy is not None and policy.then == "steps"
    assert [s.id for s in policy.steps] == ["read_saved"]


def _loop_run(h: Harness) -> WorkflowRun:
    h.ctx.tools["list_files"] = lambda path="": ["a.csv", "b.csv"]
    each = {"id": "each", "kind": "loop", "title": "Each file", "over": "files", "item": "file",
            "steps": [{**STEPS[0], "args": {"url": "{{file}}"}}]}  # fmt: skip
    workflow = parse_workflow({"version": 2, "autonomy": "proactive", "steps": [
        {"id": "ls", "kind": "tool", "title": "List", "tool": "list_files", "args": {"path": "."},
         "save_as": "files"}, each]})  # fmt: skip
    return WorkflowRun(workflow, h.ctx, InMemorySaver(), "run-1", h.on_step)


async def test_a_later_item_uses_the_plan_the_first_one_made(tmp_path: Path) -> None:
    h = Harness(tmp_path, [_plan({**READ_SAVED, "args": {"path": "{{file}}"}})])

    outcome = await _loop_run(h).start({})

    assert outcome.status == "completed"
    assert h.planned == 1
    done = [r.iteration for r in h.records if r.step_id == "fetch/added/read_saved" and
            r.status == "done"]  # fmt: skip
    assert done == [[0], [1]]


async def test_a_plan_that_names_one_items_value_is_refused_on_the_next(tmp_path: Path) -> None:
    h = Harness(tmp_path, [_plan({**READ_SAVED, "args": {"path": "a.csv"}})])

    outcome = await _loop_run(h).start({})

    assert outcome.status == "failed"
    assert outcome.error is not None and "'a.csv' is in neither" in outcome.error
