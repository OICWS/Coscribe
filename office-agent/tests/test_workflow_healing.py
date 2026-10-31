"""Self-healing (decision 0030): a failed browser step is done by a bounded agent on the page as
it is now when the task's autonomy allows it, a step that can't be taken back only with a
person's yes, and every deviation lands in the run's report."""

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langgraph.checkpoint.memory import InMemorySaver

from coscribe.workflow_spec import parse_workflow
from coscribe.workflows import run_report
from coscribe.workflows.engine import StepContext, StepRecord, WorkflowRun

from .test_workflow_agent_step import FakeModel, ScriptedRunner

GONE = 'No textbox "Company name" appeared on the page within 30s'

OPEN = {"id": "open", "kind": "tool", "title": "Open the form", "tool": "browser_navigate",
        "args": {"url": "https://forms.example.com/suppliers"}}  # fmt: skip
NAME = {"id": "name", "kind": "tool", "title": "Enter Company name", "tool": "browser_type",
        "args": {"label": "Company name", "text": "{{company}}"}}  # fmt: skip
SUBMIT = {"id": "submit", "kind": "tool", "title": "Click Submit", "tool": "browser_click",
          "args": {"label": "Submit"}, "irreversible": True}  # fmt: skip


def _fails(**_: Any) -> Any:
    raise RuntimeError(GONE)


class Harness:
    def __init__(self, tmp_path: Path, runner: ScriptedRunner, **tools: Any) -> None:
        self.records: list[StepRecord] = []
        self.runner = runner
        self.ctx = StepContext(
            tools={"browser_navigate": lambda url="": {"url": url}, **tools},
            workspace_root=tmp_path,
            state_dir=tmp_path / "state",
            make_model=lambda name: FakeModel(results=[]),
            run_agent=runner,
        )

    def run(self, steps: list[dict[str, Any]], autonomy: str | None) -> WorkflowRun:
        spec = {"inputs": [{"name": "company", "default": "Acme"}], "steps": steps}
        self.workflow = parse_workflow({**spec, "autonomy": autonomy} if autonomy else spec)
        return WorkflowRun(self.workflow, self.ctx, InMemorySaver(), "run-1", self.records.append)

    def report(self) -> dict[str, Any]:
        return run_report(self.workflow, [r.to_dict() for r in self.records])


def _done(did: str, result: str = "") -> tuple[str, str]:
    return (
        "done",
        json.dumps({"outcome": "done", "assumed": [], "did": did, "result": result, "changed": []}),
    )


async def test_a_fixed_task_fails_a_browser_step_as_it_always_did(tmp_path: Path) -> None:
    runner = ScriptedRunner([_done("typed")])
    h = Harness(tmp_path, runner, browser_type=_fails)

    outcome = await h.run([OPEN, NAME], autonomy=None).start({})

    assert (outcome.status, outcome.error) == ("failed", GONE)
    assert runner.requests == []


async def test_a_self_healing_task_has_an_agent_do_what_the_step_meant(tmp_path: Path) -> None:
    did = 'Typed "Acme" into "Legal name", the field that replaced "Company name".'
    runner = ScriptedRunner(
        [("call", "browser_snapshot", "READ"), ("call", "browser_type", "EXTERNAL"), _done(did)]
    )
    h = Harness(tmp_path, runner, browser_type=_fails)

    outcome = await h.run([OPEN, NAME], autonomy="self_healing").start({})

    assert outcome.status == "completed"
    # Inside what saving allowed (the page tools, the workflow's own site): nobody was asked.
    assert runner.log() == ["ran browser_snapshot", "ran browser_type"]
    request = runner.requests[0]
    assert request.tools is not None and "browser_type" in request.tools
    assert "browser_evaluate" not in request.tools and "browser_navigate" not in request.tools
    assert "Sites you may open: forms.example.com." in request.task
    assert GONE in request.task and '"text": "Acme"' in request.task
    done = next(r for r in h.records if r.step_id == "name" and r.status == "done")
    assert done.agent is not None and done.agent["healed"] == {
        "error": GONE,
        "did": did,
        "args": {},
    }
    healed = h.report()["healed"]
    assert healed == [{"step_id": "name", "title": "Enter Company name", "iteration": [],
                       "error": GONE, "did": did, "args": {}}]  # fmt: skip


async def test_a_healed_step_that_saves_its_output_gives_what_its_tool_would_have(
    tmp_path: Path,
) -> None:
    read = {"id": "ref", "kind": "tool", "title": "Read the reference", "tool": "browser_wait_for",
            "args": {"text": "Your reference is"}, "save_as": "ref"}  # fmt: skip
    runner = ScriptedRunner([_done('The page now says "Reference:"', "Reference: SUP-0042")])
    h = Harness(tmp_path, runner, browser_wait_for=_fails)

    outcome = await h.run([OPEN, read], autonomy="proactive").start({})

    assert outcome.status == "completed"
    assert outcome.values["ref"] == "Reference: SUP-0042"


async def test_healing_a_step_that_cant_be_taken_back_waits_for_a_person(
    tmp_path: Path,
) -> None:
    """The maintainer's choice on #754: every change the agent would make on such a step waits
    for a yes, even with no one watching."""
    runner = ScriptedRunner(
        [("call", "browser_snapshot", "READ"), ("call", "browser_click", "EXTERNAL"),
         _done('Clicked "Send application", the button that replaced "Submit".')]
    )  # fmt: skip
    h = Harness(tmp_path, runner, browser_click=_fails)
    run = h.run([OPEN, SUBMIT], autonomy="self_healing")

    first = await run.start({})

    assert first.status == "waiting"
    assert first.request is not None and first.request["pending"]["tool"] == "browser_click"
    assert runner.log() == ["ran browser_snapshot"]
    second = await run.answer(True)
    assert second.status == "completed"
    assert runner.log() == ["ran browser_snapshot", "ran browser_click"]
    assert [i["step_id"] for i in h.report()["irreversible"]] == ["submit"]


async def test_an_agent_that_cant_heal_the_step_fails_it_with_both_reasons(
    tmp_path: Path,
) -> None:
    stop = {"outcome": "stopped", "stopped_because": "The form now wants a VAT number."}
    h = Harness(tmp_path, ScriptedRunner([("done", json.dumps(stop))]), browser_type=_fails)

    outcome = await h.run([OPEN, NAME], autonomy="self_healing").start({})

    assert outcome.status == "failed"
    assert outcome.error == (
        f"{GONE} -- healing it didn't work: The agent stopped: The form now wants a VAT number."
    )
    assert h.report()["healed"] == []


async def test_a_step_that_isnt_a_browser_step_is_not_healed(tmp_path: Path) -> None:
    runner = ScriptedRunner([_done("wrote it")])
    write = {"id": "write", "kind": "tool", "title": "Write", "tool": "write_file", "args": {}}
    h = Harness(tmp_path, runner, write_file=_fails)

    outcome = await h.run([write], autonomy="self_healing").start({})

    assert outcome.status == "failed"
    assert runner.requests == []


ROWS = {"id": "rows", "kind": "tool", "title": "Rows", "tool": "rows", "save_as": "rows"}


def _each(step: dict[str, Any]) -> dict[str, Any]:
    return {"id": "each", "kind": "loop", "title": "Each row", "over": "rows", "item": "row",
            "steps": [step]}  # fmt: skip


async def test_a_later_pass_tries_what_healed_the_step_before_healing_again(
    tmp_path: Path,
) -> None:
    typed: list[dict[str, Any]] = []

    def browser_type(**args: Any) -> str:
        if args["ref"] != 'textbox "Legal name"':
            raise RuntimeError(GONE)
        typed.append(args)
        return "typed"

    name = {"id": "name", "kind": "tool", "title": "Enter Company name", "tool": "browser_type",
            "args": {"ref": 'textbox "Company name"', "text": "{{row}}"}}  # fmt: skip
    changed = ['ref: textbox "Legal name"', "text: Acme", "ref2: e12"]
    report = {"outcome": "done", "assumed": [], "did": 'Typed into "Legal name".', "result": "",
              "changed": changed}  # fmt: skip
    runner = ScriptedRunner([("done", json.dumps(report))])
    h = Harness(tmp_path, runner, browser_type=browser_type, rows=lambda: ["Acme", "Globex"])

    outcome = await h.run([OPEN, ROWS, _each(name)], autonomy="self_healing").start({})

    assert outcome.status == "completed"
    # One agent, for the first row; the second row ran the step with the healed reference.
    assert len(runner.requests) == 1
    assert typed == [{"ref": 'textbox "Legal name"', "text": "Globex"}]
    healed = h.report()["healed"]
    assert [(e["iteration"], e.get("carried", False)) for e in healed] == [
        ([0], False),
        ([1], True),
    ]
    # A reference to the row stays the row's; only a literal saved argument is replaced.
    assert healed[0]["args"] == {"ref": 'textbox "Legal name"'}


async def test_a_step_that_cant_be_taken_back_heals_with_the_person_on_every_pass(
    tmp_path: Path,
) -> None:
    report = {"outcome": "done", "assumed": [], "did": 'Clicked "Send".', "result": "",
              "changed": ['ref: button "Send"']}  # fmt: skip
    runner = ScriptedRunner([("call", "browser_click", "EXTERNAL"), ("done", json.dumps(report))])
    submit = {**SUBMIT, "args": {"ref": 'button "Submit"'}}
    h = Harness(tmp_path, runner, browser_click=_fails, rows=lambda: ["a", "b"])
    run = h.run([OPEN, ROWS, _each(submit)], autonomy="self_healing")

    outcome = await run.start({})
    asked = 0
    while outcome.status == "waiting" and asked < 5:
        asked += 1
        outcome = await run.answer(True)

    assert (outcome.status, asked) == ("completed", 2)
    assert 'Earlier in this run the same step was healed: Clicked "Send".' in (
        runner.requests[-1].task
    )
