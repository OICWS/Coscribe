"""Decision 0032: what a step does when it fails -- try again, skip it, or run other steps in its
place -- a loop that skips an item a step fails on, and the steps that run after a failed run."""

import json
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from coscribe.needs_permission import NeedsPermission
from coscribe.workflow_spec import parse_workflow, workflow_error
from coscribe.workflows import run_report, run_test, untrusted_agent_steps
from coscribe.workflows.engine import (
    StepContext,
    StepRecord,
    WorkflowNotRunnable,
    WorkflowRun,
)


class Flaky:
    """Tools that fail the first `failures[name]` calls for a path, then work."""

    def __init__(self, failures: dict[str, int] | None = None) -> None:
        self.failures = dict(failures or {})
        self.calls: list[str] = []
        self.written: list[tuple[str, str]] = []
        self.asks = 0

    def read_file(self, path: str) -> str:
        self.calls.append(path)
        if self.failures.get(path, 0) != 0:
            self.failures[path] -= 1
            raise OSError(f"{path} didn't answer")
        return f"text of {path}"

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        self.written.append((path, content))
        return {"path": path}

    def guarded(self, path: str) -> str:
        """Fails once, then asks for a folder twice -- the second time is the resume replaying
        the answer -- then works."""
        self.calls.append(path)
        if len(self.calls) == 1:
            raise OSError("the share didn't answer")
        if len(self.calls) <= 3:
            raise NeedsPermission("folder", "C:/share", "Allow C:/share?")
        return "read"


class Run:
    def __init__(self, tmp_path: Path, tools: Flaky) -> None:
        self.records: list[StepRecord] = []
        self.ctx = StepContext(
            tools={"read_file": tools.read_file, "write_file": tools.write_file,
                   "read_guarded": tools.guarded},
            workspace_root=tmp_path,
            state_dir=tmp_path / "state",
            make_model=lambda _name: None,
        )  # fmt: skip

    def start(self, workflow: dict[str, Any]) -> WorkflowRun:
        return WorkflowRun(
            parse_workflow(workflow), self.ctx, InMemorySaver(), "t", self.records.append
        )

    def last(self, step_id: str) -> StepRecord:
        return [r for r in self.records if r.step_id == step_id][-1]

    def report(self, workflow: dict[str, Any]) -> dict[str, Any]:
        # A run keeps one record per step and pass, the latest (ScheduledTriggerStore.record_step).
        stored = {(r.step_id, tuple(r.iteration)): r.to_dict() for r in self.records}
        return run_report(parse_workflow(workflow), list(stored.values()))


def _read(step_id: str, path: str, save_as: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"id": step_id, "kind": "tool", "title": step_id.title(), "tool": "read_file",
            "args": {"path": path}, "save_as": save_as or step_id, **extra}  # fmt: skip


def _write(step_id: str, content: str, **extra: Any) -> dict[str, Any]:
    return {"id": step_id, "kind": "tool", "title": step_id.title(), "tool": "write_file",
            "args": {"path": f"{step_id}.txt", "content": content}, **extra}  # fmt: skip


def _failing(then: str, retries: int = 0, steps: list[dict[str, Any]] | None = None) -> Any:
    return {"retries": retries, "wait_seconds": 0, "then": then, "steps": steps or []}


# -- one step


async def test_a_step_tried_again_counts_its_tries_and_the_run_goes_on(tmp_path: Path) -> None:
    tools = Flaky({"rates.txt": 2})
    run = Run(tmp_path, tools)
    workflow = {"steps": [_read("rates", "rates.txt", on_failure=_failing("stop", retries=3)),
                          _write("save", "{{rates}}")]}  # fmt: skip

    outcome = await run.start(workflow).start({})

    assert outcome.status == "completed"
    assert tools.calls == ["rates.txt"] * 3
    done = run.last("rates")
    assert (done.status, done.attempts, done.recovered) == ("done", 3, None)
    # Each failed try is on the record while the next one waits.
    assert [r.error for r in run.records if r.step_id == "rates" and r.error] == [
        "Try 1 didn't work: rates.txt didn't answer",
        "Try 2 didn't work: rates.txt didn't answer",
    ]
    assert tools.written == [("save.txt", "text of rates.txt")]
    report = run.report(workflow)
    assert report["retried"] == [
        {"step_id": "rates", "title": "Rates", "iteration": [], "attempts": 3, "worked": True}
    ]
    assert report["not_done"] == report["recovered"] == []


async def test_a_step_out_of_tries_stops_the_run_and_the_steps_after_a_failure_run(
    tmp_path: Path,
) -> None:
    tools = Flaky({"rates.txt": -1})
    run = Run(tmp_path, tools)
    workflow = {
        "inputs": [{"name": "month", "type": "text", "default": "2026-10"}],
        "steps": [_read("rates", "rates.txt", on_failure=_failing("stop", retries=2)),
                  _write("save", "{{rates}}")],
        "after_failure": [_write("tell", "{{month}}: {{failure.step}} -- {{failure.message}}")],
    }  # fmt: skip

    outcome = await run.start(workflow).start({})

    assert (outcome.status, outcome.step_id) == ("failed", "rates")
    assert tools.calls == ["rates.txt"] * 3
    failed = run.last("rates")
    assert (failed.status, failed.attempts, failed.recovered) == ("failed", 3, None)
    assert tools.written == [("tell.txt", "2026-10: Rates -- rates.txt didn't answer")]
    report = run.report(workflow)
    assert [i["step_id"] for i in report["not_done"]] == ["rates"]
    assert report["after_failure"] == [
        {"step_id": "tell", "title": "Tell", "iteration": [], "status": "done", "error": None}
    ]


async def test_a_skipped_step_leaves_no_result_and_is_reported_not_done(tmp_path: Path) -> None:
    tools = Flaky({"chat.txt": -1})
    run = Run(tmp_path, tools)
    workflow = {"steps": [_read("chat", "chat.txt", on_failure=_failing("skip", retries=1)),
                          _write("save", "after the chat")]}  # fmt: skip

    outcome = await run.start(workflow).start({})

    assert outcome.status == "completed"
    assert "chat" not in outcome.values
    skipped = run.last("chat")
    assert (skipped.status, skipped.attempts, skipped.recovered) == ("failed", 2, "skipped")
    assert tools.written == [("save.txt", "after the chat")]
    report = run.report(workflow)
    assert report["recovered"] == [
        {"step_id": "chat", "title": "Chat", "iteration": [], "how": "skipped",
         "error": "chat.txt didn't answer"}
    ]  # fmt: skip
    assert report["not_done"] == []
    assert report["retried"][0]["worked"] is False


async def test_steps_in_a_failed_steps_place_read_the_failure_and_make_its_result(
    tmp_path: Path,
) -> None:
    tools = Flaky({"rates.txt": -1})
    run = Run(tmp_path, tools)
    instead = [_read("saved", "saved-rates.txt", save_as="rates"),
               _write("note", "{{failure.message}}")]  # fmt: skip
    workflow = {"steps": [_read("rates", "rates.txt", on_failure=_failing("steps", 0, instead)),
                          _write("save", "{{rates}}")]}  # fmt: skip

    outcome = await run.start(workflow).start({})

    assert outcome.status == "completed"
    assert run.last("rates").recovered == "fallback"
    assert tools.written == [("note.txt", "rates.txt didn't answer"),
                             ("save.txt", "text of saved-rates.txt")]  # fmt: skip


async def test_steps_in_its_place_are_skipped_when_the_step_works(tmp_path: Path) -> None:
    tools = Flaky()
    run = Run(tmp_path, tools)
    instead = [_read("saved", "saved-rates.txt", save_as="rates")]
    workflow = {"steps": [_read("rates", "rates.txt", on_failure=_failing("steps", 1, instead)),
                          _write("save", "{{rates}}")]}  # fmt: skip

    outcome = await run.start(workflow).start({})

    assert outcome.status == "completed"
    assert tools.calls == ["rates.txt"]
    assert tools.written == [("save.txt", "text of rates.txt")]


async def test_a_pause_during_a_retry_resumes_that_try_not_the_first(tmp_path: Path) -> None:
    tools = Flaky()
    run = Run(tmp_path, tools)
    run.ctx.ask_permission = True
    step = {"id": "share", "kind": "tool", "title": "Share", "tool": "read_guarded",
            "args": {"path": "C:/share/a.txt"}, "save_as": "text",
            "on_failure": _failing("stop", retries=2)}  # fmt: skip
    workflow_run = run.start({"steps": [step]})

    waiting = await workflow_run.start({})
    assert waiting.status == "waiting"
    outcome = await workflow_run.answer(True)

    assert outcome.status == "completed"
    # Try 1 failed, try 2 asked, and only try 2 ran again on resume.
    assert len(tools.calls) == 4
    assert run.last("share").attempts == 2


# -- loops


def _loop(on_item_failure: str, steps: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"id": "each", "kind": "loop", "title": "Each file", "over": "files", "item": "file",
            "steps": steps, "on_item_failure": on_item_failure, **extra}  # fmt: skip


def _with_files(loop: dict[str, Any], files: list[Any], *after: dict[str, Any]) -> dict[str, Any]:
    listing = {"id": "ls", "kind": "script", "title": "List", "code": "print(1)", "inputs": {},
               "save_as": "files"}  # fmt: skip
    return {"steps": [listing, loop, *after], "_files": files}


async def _run_loop(tmp_path: Path, tools: Flaky, workflow: dict[str, Any]) -> tuple[Any, Run]:
    files = workflow.pop("_files")
    run = Run(tmp_path, tools)
    run.ctx.run_script = lambda *_a: {"exit_code": 0, "stdout": _json(files), "stderr": ""}
    return await run.start(workflow).start({}), run


def _json(value: Any) -> str:
    return json.dumps(value)


async def test_a_loop_skips_an_item_a_step_fails_on_and_goes_on(tmp_path: Path) -> None:
    tools = Flaky({"b.txt": -1})
    loop = _loop("skip", [_read("read", "{{file}}", save_as="text")], collect="text",
                 save_as="texts")  # fmt: skip
    workflow = _with_files(loop, ["a.txt", "b.txt", "c.txt"])

    outcome, run = await _run_loop(tmp_path, tools, workflow)

    assert outcome.status == "completed"
    assert outcome.values["texts"] == ["text of a.txt", "text of c.txt"]
    failed = [r for r in run.records if r.step_id == "read" and r.status == "failed"]
    assert [(r.iteration, r.recovered) for r in failed] == [([1], "item_skipped")]
    done = run.last("each")
    assert done.status == "done"
    assert done.output["done"] == 3
    skipped = {"index": 1, "label": "b.txt", "error": "b.txt didn't answer"}
    assert done.output["skipped"] == [skipped]
    report = run.report(workflow)
    assert report["loops"] == [{"step_id": "each", "title": "Each file", "done": 2, "total": 3,
                                "skipped": 1}]  # fmt: skip
    assert report["not_done"] == []


async def test_a_loop_whose_every_item_fails_fails(tmp_path: Path) -> None:
    tools = Flaky({"a.txt": -1, "b.txt": -1})
    workflow = _with_files(_loop("skip", [_read("read", "{{file}}")]), ["a.txt", "b.txt"])

    outcome, run = await _run_loop(tmp_path, tools, workflow)

    assert (outcome.status, outcome.step_id) == ("failed", "each")
    assert outcome.error == "Every item failed. The last: b.txt didn't answer"
    assert run.last("each").output["skipped"][1]["label"] == "b.txt"


async def test_an_inner_loop_that_stops_skips_the_outer_item(tmp_path: Path) -> None:
    tools = Flaky({"b.txt": -1})
    inner = {"id": "pages", "kind": "loop", "title": "Each page", "over": "file.pages",
             "item": "page", "steps": [_read("read", "{{page}}")]}  # fmt: skip
    workflow = _with_files(
        _loop("skip", [inner]),
        [{"name": "one", "pages": ["a.txt"]}, {"name": "two", "pages": ["b.txt", "c.txt"]},
         {"name": "three", "pages": ["d.txt"]}],
    )  # fmt: skip

    outcome, run = await _run_loop(tmp_path, tools, workflow)

    assert outcome.status == "completed"
    assert tools.calls == ["a.txt", "b.txt", "d.txt"]
    stopped = [r for r in run.records if r.step_id == "pages" and r.status == "failed"]
    assert [(r.iteration, r.recovered) for r in stopped] == [([1], "item_skipped")]
    assert run.last("each").output["skipped"][0]["label"] == "two"


async def test_a_step_that_skips_itself_inside_a_skipping_loop_keeps_the_item(
    tmp_path: Path,
) -> None:
    tools = Flaky({"b.txt": -1})
    steps = [_read("read", "{{file}}", on_failure=_failing("skip")), _write("save", "{{file}}")]
    workflow = _with_files(_loop("skip", steps), ["a.txt", "b.txt"])

    outcome, run = await _run_loop(tmp_path, tools, workflow)

    assert outcome.status == "completed"
    assert [path for path, _ in tools.written] == ["save.txt", "save.txt"]
    assert "skipped" not in run.last("each").output


# -- after a failed run


async def test_the_steps_after_a_failed_run_never_wait_for_a_person(tmp_path: Path) -> None:
    tools = Flaky({"rates.txt": -1})
    run = Run(tmp_path, tools)
    run.ctx.ask_permission = True
    tell = {"id": "tell", "kind": "tool", "title": "Tell", "tool": "read_guarded",
            "args": {"path": "x"}}  # fmt: skip
    workflow = {"steps": [_read("rates", "rates.txt")], "after_failure": [tell]}

    outcome = await run.start(workflow).start({})

    assert (outcome.status, outcome.step_id) == ("failed", "rates")
    assert run.last("tell").status == "failed"
    assert not [r for r in run.records if r.status == "waiting"]


async def test_a_run_that_works_never_runs_the_steps_after_a_failure(tmp_path: Path) -> None:
    tools = Flaky()
    run = Run(tmp_path, tools)
    workflow = {"steps": [_read("rates", "rates.txt")], "after_failure": [_write("tell", "x")]}

    outcome = await run.start(workflow).start({})

    assert outcome.status == "completed"
    assert tools.written == []


# -- what is refused, and what the graph and the permissions see


def test_a_step_that_cant_be_undone_is_never_tried_again() -> None:
    step = _write("pay", "x", irreversible=True, on_failure=_failing("skip", retries=1))
    with pytest.raises(ValidationError, match="never tried again"):
        parse_workflow({"steps": [step]})
    parse_workflow({"steps": [{**step, "on_failure": _failing("skip")}]})


async def test_a_run_with_nothing_in_a_failed_steps_place_is_refused(tmp_path: Path) -> None:
    run = Run(tmp_path, Flaky())
    workflow = {"steps": [_read("rates", "rates.txt", on_failure=_failing("steps"))]}

    with pytest.raises(WorkflowNotRunnable, match="step 1: no steps run in its place"):
        await run.start(workflow).start({})


def test_an_agent_that_reads_a_failure_reads_outside_content() -> None:
    agent = {"id": "explain", "kind": "agent", "title": "Explain", "goal": "{{failure.message}}",
             "tools": ["write_file"]}  # fmt: skip
    workflow = parse_workflow(
        {"version": 2, "steps": [_read("rates", "rates.txt")], "after_failure": [agent]}
    )

    assert untrusted_agent_steps(workflow, frozenset()) == ["explain"]


async def test_a_test_run_guards_a_step_in_a_failed_steps_place_and_leaves_out_others(
    tmp_path: Path,
) -> None:
    tools = Flaky({"rates.txt": -1})
    run = Run(tmp_path, tools)
    workflow = parse_workflow({
        "steps": [_read("rates", "rates.txt",
                        on_failure=_failing("steps", 0, [_write("pay", "x", irreversible=True)]))],
        "after_failure": [_write("mail", "x", irreversible=True), _write("log", "failed")],
    })  # fmt: skip

    result = await run_test(workflow, run.ctx)

    assert result["status"] == "stopped_before_irreversible"
    assert result["stopped_before"] == {"id": "pay", "title": "Pay"}
    assert tools.written == []


def test_a_problem_in_a_failed_steps_place_or_after_a_failure_names_its_step_number() -> None:
    broken = {"id": "broken", "kind": "tool", "title": "Broken", "args": {}}
    data = {
        "steps": [_read("rates", "rates.txt", on_failure=_failing("steps", 0, [broken])),
                  _write("save", "x")],
        "after_failure": [_write("tell", "x"), {**broken, "id": "late"}],
    }  # fmt: skip

    with pytest.raises(ValidationError) as caught:
        parse_workflow(data)

    message = workflow_error(caught.value, data)
    assert message.startswith("step 2: tool: Field required")
    assert "step 5: tool: Field required" in message


async def test_a_run_a_person_said_no_to_runs_no_steps_after_a_failure(tmp_path: Path) -> None:
    tools = Flaky()
    run = Run(tmp_path, tools)
    ask = {"id": "ask", "kind": "approval", "title": "Ask", "message": "Go on?"}
    workflow_run = run.start({"steps": [ask], "after_failure": [_write("tell", "x")]})

    await workflow_run.start({})
    outcome = await workflow_run.answer(False)

    assert outcome.status == "failed"
    assert tools.written == []
