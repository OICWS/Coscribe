# ruff: noqa: E402
"""How many tokens a run's models may use before a person is asked (decision 0043): an agent step
that used its share, and a run past what its task's runs use, pause with a question; nothing is
asked twice across pauses, and a "stop" ends the step as a person's no."""

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.workflow_spec import parse_workflow
from coscribe.workflows import StepContext, StepRecord, WorkflowRun, run_budget
from tests.test_workflow_agent_runner import Env, _agent, _calls, _says


def _costs(message: AIMessage, tokens: int = 600) -> AIMessage:
    message.usage_metadata = {"input_tokens": tokens, "output_tokens": 0, "total_tokens": tokens}
    return message


def _read() -> AIMessage:
    return _costs(_calls(("read_file", {"path": "in.txt"})))


def _run(env: Env, steps: list[dict[str, Any]], step_tokens: int = 1000, **ctx: Any) -> WorkflowRun:
    context = StepContext(
        step_tokens=step_tokens,
        tools={t.__name__: t for t in env.tools},
        workspace_root=env.tmp_path,
        state_dir=env.tmp_path / "state",
        make_model=lambda _name: env.model,
        run_agent=env.runner(),
        **ctx,
    )

    def on_step(record: StepRecord) -> None:
        env.records.append(record)
        if context.budget is not None:
            context.budget.count(record)

    workflow = parse_workflow({"version": 2, "steps": steps})
    return WorkflowRun(workflow, context, env.checkpointer, "run-1", on_step)


async def test_an_agent_that_used_its_share_asks_and_goes_on_where_it_stopped(
    tmp_path: Path,
) -> None:
    env = Env(tmp_path, [_read(), _read(), _costs(_says("Sorted."))])
    run = _run(env, [_agent(autonomy="high")])

    waiting = await run.start({})

    assert waiting.status == "waiting"
    assert waiting.request is not None
    asked = {"kind": "tokens", "until": None, "scope": "step", "used": 1200}
    assert waiting.request["pause"] == asked
    waits = [r for r in env.records if r.status == "waiting"]
    assert waits[-1].pause == asked
    assert "1k new tokens" in str(waits[-1].output)
    done = await run.answer(True)
    assert done.status == "completed"
    assert done.values["sorted"] == {"report": "Sorted."}
    assert env.model.i == 3
    assert env.ran == ["read in.txt", "read in.txt"]


async def test_stop_ends_the_step_as_a_persons_no(tmp_path: Path) -> None:
    env = Env(tmp_path, [_read(), _read(), _says("never asked")])
    run = _run(env, [_agent(autonomy="high")])
    await run.start({})

    outcome = await run.answer(False)

    assert outcome.status == "failed"
    assert outcome.declined
    assert outcome.error is not None and outcome.error.startswith("Stopped: Sort the mail")
    assert env.model.i == 2


async def test_an_answer_is_never_taken_for_another_pause_in_the_step(tmp_path: Path) -> None:
    write = _costs(_calls(("write_file", {"path": "out.txt", "content": "x"})))
    env = Env(tmp_path, [_read(), _read(), write, _costs(_says("Wrote it."))])
    run = _run(env, [_agent(autonomy="high")])

    await run.start({})
    call = await run.answer(True)

    assert call.status == "waiting"
    assert call.request is not None and call.request["pending"]["tool"] == "write_file"
    done = await run.answer(True)
    assert done.status == "completed"
    assert env.ran == ["read in.txt", "read in.txt", "write out.txt"]
    assert env.model.i == 4


async def test_a_call_answered_before_the_question_is_not_asked_again(tmp_path: Path) -> None:
    write = _costs(_calls(("write_file", {"path": "out.txt", "content": "x"})))
    env = Env(tmp_path, [write, _read(), _costs(_says("Done."))])
    run = _run(env, [_agent(autonomy="high")])

    await run.start({})
    tokens = await run.answer(True)

    assert tokens.status == "waiting"
    assert tokens.request is not None and tokens.request["pause"]["scope"] == "step"
    done = await run.answer(True)
    assert done.status == "completed"
    assert env.ran == ["write out.txt", "read in.txt"]


async def test_a_run_past_its_cap_asks_before_its_next_model_step(tmp_path: Path) -> None:
    kept: list[int] = []
    env = Env(tmp_path, [_read(), _costs(_says("First.")), _costs(_says("Second."))])
    budget = run_budget([], [], None, kept.append)
    budget.cap = budget.grant = 1000
    second = {**_agent(autonomy="high"), "id": "again", "title": "Again", "save_as": "again"}
    run = _run(env, [_agent(autonomy="high"), second], step_tokens=10_000, budget=budget)

    waiting = await run.start({})

    assert waiting.status == "waiting" and waiting.step_id == "again"
    assert waiting.request is not None
    assert waiting.request["pause"]["scope"] == "run"
    assert waiting.request["pause"]["used"] == 1200
    done = await run.answer(True)
    assert done.status == "completed"
    assert kept == [2200]


def test_a_runs_cap_follows_what_its_tasks_runs_used() -> None:
    def used(tokens: int) -> list[dict[str, Any]]:
        return [{"status": "done", "agent": {"tokens": tokens}}, {"status": "running"}]

    assert run_budget([], [], None).cap == 2_000_000
    big = run_budget([used(400_000), used(1_000_000)], used(5_000), None)
    assert (big.cap, big.grant, big.spent) == (3_000_000, 3_000_000, 5_000)
    assert run_budget([], [], 4_000_000).cap == 4_000_000
    # What a provider served from its cache is billed far lower, and isn't counted.
    cached = [{"status": "done", "agent": {"tokens": 900_000, "cached_tokens": 800_000}}]
    assert run_budget([cached], cached, None).spent == 100_000
