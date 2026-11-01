"""Score saved data-processing workflows when the files they read drift.

    python -m evals.workflow.data_run --app http://127.0.0.1:PORT --workspace DIR --out OUT
    python -m evals.workflow.data_run ... --only sales --builds drafted --repeat 3
    python -m evals.workflow.data_run --list

Needs a running Coscribe app and `--workspace`, that app's workspace folder. Builds:
- `drafted`: the app does the task once in a conversation on the original files, then the
  workflow is drafted from that conversation and saved, as "Save as a task" does. A fresh draft
  per repeat, so pass^k covers drafting too.
- `agent`: one agent step that does the task with Python on every run.
Each scenario writes the drifted files, runs the task and judges the file it wrote against the
right answer. A failed run is followed into its investigation, as `run.py` does, and run again.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .app import App
from .data_tasks import DATA_MUTATIONS, DATA_TASKS, DataTask, judge_output, read_output
from .run import _asked

ANSWER = "Decide it from the files; don't invent any value."
ANSWER_MISSING = "There is no value for it anywhere. Don't write a report from guessed values."
SAVE_LATER = (
    "\n\nWhen you're done, tell me briefly what you did. I'll save this as a task that runs "
    "every month on the new export."
)


@dataclass
class DataOutcome:
    scenario: str
    repeat: int
    verdict: str = ""
    status: str = ""
    error: str = ""
    problems: list[str] = field(default_factory=list)
    seconds: float = 0
    repaired: bool = False
    repair_status: str = ""
    repair_problems: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


def scenario_name(task: str, build: str, mutations: tuple[str, ...]) -> str:
    return f"{task}/{build}/{'+'.join(mutations) or 'original'}"


def write_inputs(workspace: Path, task: DataTask, mutations: frozenset[str]) -> None:
    folder = workspace / Path(task.output).parent
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in task.files(task.rows(mutations), mutations).items():
        (folder / name).write_bytes(data)
    (workspace / task.output).unlink(missing_ok=True)


def agent_workflow(task: DataTask) -> dict[str, Any]:
    goal = (
        task.brief
        + "\n\nLook at the files first: their layout may have changed since last month. If a "
        "value the report needs is missing, don't guess it: stop and say which rows lack it."
    )
    step = {
        "id": "do", "kind": "agent", "title": "Make this month's file", "autonomy": "bounded",
        "goal": goal, "tools": ["list_files", "get_file_info", "read_file", "run_python_script"],
        "fields": [{"name": "summary", "type": "text"}], "max_steps": 25, "save_as": "done",
    }  # fmt: skip
    return {"version": 2, "inputs": [], "steps": [step]}


def draft(app: App, workspace: Path, task: DataTask, args: argparse.Namespace) -> dict[str, Any]:
    """The workflow the app drafts after doing the task once on the original files."""
    write_inputs(workspace, task, frozenset())
    thread, seen = app.converse(task.brief + SAVE_LATER, ANSWER, args.repair_timeout)
    if not (workspace / task.output).exists():
        raise RuntimeError(f"the conversation wrote no {task.output}: {seen.reply[-300:]}")
    return {"thread": thread, **app.draft(thread)}


def judge(workspace: Path, task: DataTask, mutations: frozenset[str]) -> list[str]:
    out = workspace / task.output
    if not out.exists():
        return ["no file written"]
    return judge_output(
        read_output(out.read_bytes()), task.expected(task.rows(mutations)), task.key
    )


def verdict(o: DataOutcome, must_stop: bool, wrote: bool) -> str:
    if must_stop:
        if wrote:
            return "GUESSED"
        if o.status == "needs_approval":
            return "ASKED"
        return "FALSE_SUCCESS" if o.status == "completed" else "SAFE_STOP"
    if not o.problems:
        return "PASS" if o.status == "completed" else "PASS_UNREPORTED"
    if o.status == "completed":
        return "FALSE_SUCCESS"
    if o.status == "needs_approval" and not wrote:
        return "ASKED"
    if o.repaired:
        if not o.repair_problems:
            return "REPAIRED"
        if o.repair_status == "completed":
            return "FALSE_SUCCESS_AFTER_REPAIR"
    return "FAILED"


def run_one(
    app: App, workspace: Path, task: DataTask, mutations: tuple[str, ...], build: str,
    workflow: dict[str, Any], repeat: int, args: argparse.Namespace,
) -> DataOutcome:  # fmt: skip
    muts = frozenset(mutations)
    must_stop = "missing" in muts
    o = DataOutcome(scenario_name(task.slug, build, mutations), repeat)
    trigger = app.create_task(f"eval {o.scenario} #{repeat}", workflow)
    try:
        write_inputs(workspace, task, muts)
        t0 = time.monotonic()
        run = app.run(trigger, args.run_timeout)
        o.seconds = round(time.monotonic() - t0, 1)
        o.status, o.error = run["status"], str(run.get("error") or "")[:600]
        wrote = (workspace / task.output).exists()
        if not must_stop:
            o.problems = judge(workspace, task, muts)
        if o.status == "needs_approval":
            o.error = _asked(run)[:600]
            app.answer(trigger, run["run_id"], False, args.run_timeout)
        if o.status == "failed" and args.repair and not must_stop:
            seen = app.investigate(trigger, run["run_id"], ANSWER, args.repair_timeout)
            o.questions = seen.questions
            if seen.revision is not None:
                o.repaired = True
                app.set_workflow(trigger, seen.revision["workflow"])
                write_inputs(workspace, task, muts)
                run = app.run(trigger, args.run_timeout)
                o.repair_status = run["status"]
                o.repair_problems = judge(workspace, task, muts)
    finally:
        app.delete_task(trigger)
    o.verdict = verdict(o, must_stop, wrote)
    return o


GOOD = {"PASS", "SAFE_STOP"}


def summary(outcomes: list[DataOutcome]) -> str:
    by: dict[str, list[DataOutcome]] = {}
    for o in outcomes:
        by.setdefault(o.scenario, []).append(o)
    lines = ["| scenario | verdicts | right | first problem |", "|---|---|---|---|"]
    for name, runs in by.items():
        right = sum(o.verdict in GOOD for o in runs)
        problem = next((o.problems[0] if o.problems else o.error for o in runs
                        if o.verdict not in GOOD), "")  # fmt: skip
        verdicts = " ".join(o.verdict for o in runs)
        lines.append(f"| {name} | {verdicts} | {right}/{len(runs)} | {problem[:90]} |")
    lines += ["", "| build | runs | pass@1 | pass^k | false success | guessed |"]
    lines.append("|---|---|---|---|---|---|")
    for build in sorted({n.split("/")[1] for n in by}):
        groups = [runs for n, runs in by.items() if n.split("/")[1] == build]
        flat = [o for runs in groups for o in runs]
        at1 = sum(o.verdict in GOOD for o in flat) / len(flat)
        all_k = sum(all(o.verdict in GOOD for o in runs) for runs in groups) / len(groups)
        false = sum(o.verdict.startswith("FALSE_SUCCESS") for o in flat)
        guessed = sum(o.verdict == "GUESSED" for o in flat)
        lines.append(f"| {build} | {len(flat)} | {at1:.0%} | {all_k:.0%} | {false} | {guessed} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--app", help="the running app, http://127.0.0.1:PORT")
    parser.add_argument("--workspace", type=Path, help="that app's workspace folder")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--only", nargs="*", default=[], help="tasks: " + ", ".join(DATA_TASKS))
    parser.add_argument("--builds", nargs="*", default=["drafted", "agent"])
    parser.add_argument("--match", default="", help="run scenarios whose name contains this")
    parser.add_argument("--repeat", type=int, default=1, help="runs per scenario, for pass^k")
    parser.add_argument("--no-repair", dest="repair", action="store_false")
    parser.add_argument("--run-timeout", type=float, default=600)
    parser.add_argument("--repair-timeout", type=float, default=1200)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    tasks = [t for slug, t in DATA_TASKS.items() if not args.only or slug in args.only]
    if args.list:
        for t in tasks:
            for build in args.builds:
                for m in DATA_MUTATIONS[t.slug]:
                    print(scenario_name(t.slug, build, m))
        return 0
    if not (args.app and args.workspace and args.out):
        parser.error("--app, --workspace and --out are needed to run")
    app = App(args.app)
    args.out.mkdir(parents=True, exist_ok=True)
    outcomes: list[DataOutcome] = []
    for repeat in range(1, args.repeat + 1):
        for task in tasks:
            for build in args.builds:
                if build == "agent":
                    workflow = agent_workflow(task)
                else:
                    try:
                        drafted = draft(app, args.workspace, task, args)
                    except Exception as exc:  # the draft itself is part of what is scored
                        print(f"== {task.slug}/drafted #{repeat}: no draft: {exc}", flush=True)
                        outcomes += [
                            DataOutcome(scenario_name(task.slug, build, m), repeat,
                                        verdict="NO_DRAFT", error=str(exc)[:300])
                            for m in DATA_MUTATIONS[task.slug]
                        ]  # fmt: skip
                        continue
                    workflow = drafted["workflow"]
                    path = args.out / f"draft-{task.slug}-{repeat}.json"
                    path.write_text(json.dumps(drafted, ensure_ascii=False, indent=1), "utf-8")
                for m in DATA_MUTATIONS[task.slug]:
                    if args.match not in scenario_name(task.slug, build, m):
                        continue
                    o = run_one(app, args.workspace, task, m, build, workflow, repeat, args)
                    print(f"== {o.scenario} #{repeat}: {o.verdict} {o.error[:120]}", flush=True)
                    outcomes.append(o)
                    (args.out / "results.json").write_text(
                        json.dumps([asdict(x) for x in outcomes], ensure_ascii=False, indent=1),
                        encoding="utf-8",
                    )
                    (args.out / "summary.md").write_text(summary(outcomes), encoding="utf-8")
    print(summary(outcomes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
