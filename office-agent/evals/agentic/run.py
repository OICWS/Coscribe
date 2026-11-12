"""Run the multi-turn tasks through coscribe's real agent and measure how far each conversation
gets on its own.

    python -m evals.agentic.run --tasks all --out evals/runs/agentic-main
    python -m evals.agentic.run --tasks 01,06 --out evals/runs/agentic-try
    python -m evals.agentic.run --tasks 01,10 --out evals/runs/tape --record evals/agentic/tapes
    python -m evals.agentic.run --tasks 01,10 --out evals/runs/replay --replay    # no model

Each task gets a fresh workspace and a `ChatSessionLG` built the way the eval runner builds one,
but in the tier of a person at the keyboard: questions and approvals reach the scripted user,
which approves, saves what `remember` offers and answers anything else with "decide it
yourself". The turns are sent in order; if a check then fails, one generic nudge is sent and the
checks run again. `result.json` per task and `summary.md` / `summary.json` for the run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import run as office
from ..prices import cost
from . import replay
from .tasks import NUDGE, AgenticTask, Outcome, select

TURN_TIMEOUT = 900.0
# A compaction's summary has these headings (runtime/compaction.py); a reply carrying them is
# the summary leaking into the chat.
SUMMARY_HEADINGS = ("## Requests", "## Current work")


@dataclass
class Turn:
    calls: list[tuple[str, str]] = field(default_factory=list)
    replies: list[str] = field(default_factory=list)


@dataclass
class ScriptedUser(office.Recorder):
    """The person at the keyboard: approves, saves what remember offers, answers the rest with
    "decide it yourself", and keeps every call with its arguments per turn."""

    turns: list[Turn] = field(default_factory=list)
    approvals: int = 0
    saves: int = 0

    async def send_json(self, data: dict[str, Any]) -> None:
        kind = data.get("type")
        if kind == "tool_started" and self.turns:
            arguments = json.dumps(data.get("arguments") or {}, sort_keys=True, ensure_ascii=False)
            self.turns[-1].calls.append((data["tool_name"], arguments))
        elif kind == "agent_message" and self.turns:
            self.turns[-1].replies.append(data["text"])
        if kind == "approval_required":
            self.approvals += 1
        if kind == "question_required" and _is_remember(data["questions"]):
            self.saves += 1
            self.questions += 1
            self.session.resolve_question(data["id"], ["Save everywhere" for _ in data["questions"]])
            return
        await super().send_json(data)


def _is_remember(questions: list[dict[str, Any]]) -> bool:
    return any("global instructions" in str(q.get("question", "")) for q in questions)


def repeated_calls(turns: list[Turn]) -> dict[str, int]:
    """Calls made again with the same arguments in the same turn, by tool."""
    repeats: Counter[str] = Counter()
    for turn in turns:
        seen: set[tuple[str, str]] = set()
        for call in turn.calls:
            if call in seen:
                repeats[call[0]] += 1
            seen.add(call)
    return dict(repeats)


def summary_leaks(turns: list[Turn]) -> int:
    return sum(
        1 for turn in turns for reply in turn.replies if any(h in reply for h in SUMMARY_HEADINGS)
    )


def open_tasks(tasks: list[dict[str, Any]]) -> int:
    return sum(1 for task in tasks if task.get("status") != "completed")


def run_checks(task: AgenticTask, outcome: Outcome) -> dict[str, bool]:
    return {name: check(outcome) for name, check in task.checks.items()}


def _outcome(task_out: Path, workspace: Path, thread_id: str, turns: list[Turn]) -> Outcome:
    memory = task_out / "MEMORY.md"
    tasks_file = task_out / "state" / f"{thread_id}.tasks.json"
    return Outcome(
        replies=[turn.replies for turn in turns],
        calls=[f"{name} {arguments}" for turn in turns for name, arguments in turn.calls],
        workspace=workspace,
        memory=memory.read_text(encoding="utf-8") if memory.is_file() else "",
        tasks=json.loads(tasks_file.read_text(encoding="utf-8")) if tasks_file.is_file() else [],
    )


def _build(
    task: AgenticTask,
    task_out: Path,
    workspace: Path,
    model: str,
    effort: str,
    window: int | None = None,
) -> Any:
    # Settings read the threshold from the environment while the session is built, and nothing
    # awaits in between, so tasks running side by side each get their own.
    previous = os.environ.get("COSCRIBE_AUTO_COMPACT_THRESHOLD")
    os.environ["COSCRIBE_AUTO_COMPACT_THRESHOLD"] = str(task.compact_threshold)
    try:
        session = office._build_session(
            task_out,
            workspace,
            model,
            task.name,
            effort,
            window=window,
            connectors=task.connectors,
        )
    finally:
        if previous is None:
            os.environ.pop("COSCRIBE_AUTO_COMPACT_THRESHOLD", None)
        else:
            os.environ["COSCRIBE_AUTO_COMPACT_THRESHOLD"] = previous
    session.run_approval_mode = None
    return session


async def _send(session: Any, user: ScriptedUser, text: str, errors: list[str]) -> None:
    user.turns.append(Turn())
    try:
        await asyncio.wait_for(session.handle_user_message(text, user), TURN_TIMEOUT)
    except TimeoutError:
        errors.append(f"no end of turn after {TURN_TIMEOUT:.0f} s")
    except Exception as exc:  # noqa: BLE001 -- one task failing must not stop the run
        errors.append(f"{type(exc).__name__}: {exc}")


async def run_task(
    task: AgenticTask,
    out: Path,
    model: str,
    effort: str,
    *,
    record: Path | None = None,
    tape_file: Path | None = None,
) -> dict[str, Any]:
    """Run one task. With `record`, a run that completed leaves its tape in that folder; with
    `tape_file`, the answers come from that tape (inside `replay.taped_models()`)."""
    task_out = out.resolve() / task.name
    if task_out.exists():
        shutil.rmtree(task_out)
    workspace = task_out / "workspace"
    workspace.mkdir(parents=True)
    task.setup(workspace)

    usage = office.Usage()
    office._CURRENT_USAGE.set(usage)
    user = ScriptedUser(can_resolve_approvals=True)
    errors: list[str] = []
    started = time.monotonic()
    tape = None
    if tape_file is not None:
        tape = replay.Tape.load(tape_file, workspace, task_out)
    elif record is not None:
        tape = replay.Tape(task.name, model, effort)
    if tape is not None:
        replay.use(tape)
    session = _build(task, task_out, workspace, model, effort, tape.window if tape_file else None)
    user.session = session
    for text in task.turns:
        await _send(session, user, text, errors)
    outcome = _outcome(task_out, workspace, task.name, user.turns)
    first = run_checks(task, outcome)
    left_open = open_tasks(outcome.tasks)
    after_nudge = None
    if not all(first.values()):
        await _send(session, user, NUDGE, errors)
        after_nudge = run_checks(task, _outcome(task_out, workspace, task.name, user.turns))

    result = {
        "task": task.name,
        "model": model,
        "effort": effort,
        "completed": all(first.values()),
        "completed_after_nudge": None if after_nudge is None else all(after_nudge.values()),
        "checks": first,
        "checks_after_nudge": after_nudge,
        "open_tasks_at_end": left_open,
        "repeated_calls": repeated_calls(user.turns),
        "summary_leaks": summary_leaks(user.turns),
        "questions": user.questions,
        "approvals": user.approvals,
        "remember_saves": user.saves,
        "tool_call_count": sum(len(turn.calls) for turn in user.turns),
        "tool_calls": dict(user.tool_calls),
        "tool_errors": user.tool_errors,
        "errors": errors + user.errors,
        "wall_seconds": round(time.monotonic() - started, 1),
        "model_calls": usage.model_calls,
        "input_tokens": usage.input_tokens,
        "cached_tokens": usage.cached_tokens,
        "output_tokens": usage.output_tokens,
        "cost": cost(model, usage.input_tokens, usage.cached_tokens, usage.output_tokens),
        "turns": [{"calls": turn.calls, "replies": turn.replies} for turn in user.turns],
    }
    called = [[name for name, _arguments in turn.calls] for turn in user.turns]
    if tape is not None and tape_file is not None:
        result["tape"] = {"answers_left": tape.left(), "calls_as_recorded": called == tape.calls}
    elif tape is not None and record is not None and result["completed"] and not result["errors"]:
        tape.calls = called
        tape.window = session._context_window_client.get_context_window(model)
        tape.save(record / f"{task.name}.json", workspace, task_out)
    (task_out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.rmtree(task_out / "state" / "script-env", ignore_errors=True)
    return result


async def replay_task(task: AgenticTask, tape_file: Path, out: Path) -> dict[str, Any]:
    """Run `task` from its tape, with no model, at the model name and effort it was recorded at.
    The result's `tape` says whether every answer was used and the same tools were called."""
    recorded = json.loads(tape_file.read_text(encoding="utf-8"))
    with replay.taped_models():
        return await run_task(
            task, out, recorded["model"], recorded["effort"], tape_file=tape_file
        )


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """The run's numbers: what the plan's later steps are measured against."""
    count = len(results)
    completed = sum(1 for r in results if r["completed"])
    rescued = sum(1 for r in results if r["completed_after_nudge"])
    costs = [r["cost"] for r in results if r["cost"] is not None]
    return {
        "tasks": count,
        "completed": completed,
        "completed_after_nudge": rescued,
        "needed_a_nudge": sum(1 for r in results if r["completed_after_nudge"] is not None),
        "open_tasks_at_end": sum(r["open_tasks_at_end"] for r in results),
        "repeated_calls": sum(sum(r["repeated_calls"].values()) for r in results),
        "summary_leaks": sum(r["summary_leaks"] for r in results),
        "questions": sum(r["questions"] for r in results),
        "approvals": sum(r["approvals"] for r in results),
        "tool_calls": sum(r["tool_call_count"] for r in results),
        "tool_errors": sum(len(r["tool_errors"]) for r in results),
        "seconds": round(sum(r["wall_seconds"] for r in results), 1),
        "cost": round(sum(costs), 4) if costs else None,
    }


def _mark(value: bool | None) -> str:
    return "-" if value is None else ("yes" if value else "no")


def write_summary(out: Path, results: list[dict[str, Any]]) -> str:
    totals = summarize(results)
    lines = [
        "| task | done | after nudge | open tasks | repeats | leaks | questions | approvals "
        "| tool calls | s | cost |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        cost_cell = "-" if r["cost"] is None else f"{r['cost']:.4f}"
        lines.append(
            f"| {r['task']} | {_mark(r['completed'])} | {_mark(r['completed_after_nudge'])} "
            f"| {r['open_tasks_at_end']} | {sum(r['repeated_calls'].values())} "
            f"| {r['summary_leaks']} | {r['questions']} | {r['approvals']} "
            f"| {r['tool_call_count']} | {r['wall_seconds']} | {cost_cell} |"
        )
    lines.append("")
    lines.append(
        f"Completed {totals['completed']}/{totals['tasks']} without help, "
        f"{totals['completed_after_nudge']} more after one nudge; cost {totals['cost']}."
    )
    text = "\n".join(lines) + "\n"
    (out / "summary.md").write_text(text, encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps({"totals": totals, "tasks": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return text


async def run_all(args: argparse.Namespace, tasks: list[AgenticTask], out: Path) -> list[Any]:
    gate = asyncio.Semaphore(args.jobs)

    async def one(task: AgenticTask) -> dict[str, Any]:
        async with gate:
            print(f"start {task.name}", flush=True)
            if args.replay:
                result = await replay_task(task, replay.TAPES / f"{task.name}.json", out)
            else:
                result = await run_task(task, out, args.model, args.effort, record=args.record)
            print(
                f"done  {task.name}: completed={result['completed']} "
                f"after_nudge={result['completed_after_nudge']} cost={result['cost']}",
                flush=True,
            )
            return result

    return list(await asyncio.gather(*(one(t) for t in tasks)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--tasks", default="all", help="`all`, or names / number prefixes")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=office.DEFAULT_MODEL)
    parser.add_argument("--effort", choices=office.EFFORT_LEVELS, default=office.DEFAULT_EFFORT)
    parser.add_argument("--jobs", type=int, default=2, help="tasks run at the same time")
    parser.add_argument(
        "--record", type=Path, help="keep each completed task's answers as a tape in this folder"
    )
    parser.add_argument(
        "--replay", action="store_true", help="answer from evals/agentic/tapes, with no model"
    )
    args = parser.parse_args(argv)
    if "DEEPSEEK_API_KEY" not in os.environ and not args.replay:
        print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
        return 1
    tasks = select(args.tasks)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    with office.measured_models(), replay.recorded_models():
        results = asyncio.run(run_all(args, tasks, out))
    print(write_summary(out, results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
