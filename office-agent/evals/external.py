"""Run public office benchmarks through coscribe's real agent and grade them with each
benchmark's own checker.

    python -m evals.external --bench officeval --data <dataset> --grader <repo> \\
        --tasks 003,033 --out evals/runs/officeval-smoke
    python -m evals.external --bench spreadsheetbench --data <spreadsheetbench_verified_400> \\
        --grader <SpreadsheetBench repo> --tasks 13-1,10452 --out evals/runs/sb-smoke

- OmegaUse-OfficeVal (https://github.com/baidu-frontier-research/OmegaUse-OfficeVal, Apache-2.0):
  `--data` is a download of the Hugging Face dataset (`tasks/`, `task_files/`), `--grader` a
  checkout of the repository, whose `verifiers/officeval_NNN_verifier.py` scores the Office files
  the agent changed or made, collected into a folder named after the task as the benchmark's
  submission layout asks.
- SpreadsheetBench Verified (https://github.com/RUCKBReasoning/SpreadsheetBench, CC BY-SA 4.0):
  `--data` is the unpacked `spreadsheetbench_verified_400`, `--grader` a checkout of the
  repository, whose `evaluation/evaluation.py` compares the answer range of the agent's workbook,
  recalculated by LibreOffice as its `open_spreadsheet.py` does, with the golden one.

Neither benchmark nor its data is copied into this repository. The agent session, usage and cost
are the ones `evals.run` records; a task's folder holds `result.json`, `grade.json` and the
workspace, and the run's `summary.json` the score and cost of each task.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import run as base
from .prices import cost

OFFICE_SUFFIXES = (".docx", ".xlsx", ".xlsm", ".pptx", ".pdf")
# The six verifiers that need Word through COM on Windows; the benchmark skips them elsewhere.
OFFICEVAL_COM = frozenset({"001", "021", "023", "024", "025", "039"})
GRADE_TIMEOUT = 600

_OFFICEVAL_BRIEF = (
    "Complete the following Office-suite task using the input files in the workspace:\n\n"
    "{instruction}\n\n"
    "Create or modify every final deliverable requested by the task. Preserve the requested "
    "formats and keep every final deliverable directly in the workspace, not in a subfolder."
)
_SPREADSHEET_BRIEF = (
    "Solve this spreadsheet task on the workbook `{name}` in the workspace.\n\n"
    "### Instruction\n{instruction}\n\n"
    "### Where the answer goes\n"
    "{kind}: {position}. Only change cells inside that range; the rest of the workbook stays "
    "as it is.\n\n"
    "Save the finished workbook as `output.xlsx` in the workspace, and keep `{name}` unchanged."
)


@dataclass
class ExternalTask:
    name: str
    brief: str
    inputs: list[Path]
    grade: Callable[[Path, Path], dict[str, Any]]


def officeval_tasks(data: Path, grader: Path, wanted: list[str], python: str) -> list[ExternalTask]:
    tasks = []
    for number in wanted:
        spec = json.loads((data / "tasks" / f"officeval_{number}.json").read_text(encoding="utf-8"))
        folder = data / "task_files" / spec["id"]
        inputs = [folder / item["dest"] for item in spec["origin_files"]]
        missing = [str(p) for p in inputs if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"{spec['id']}: not downloaded: {', '.join(missing)}")
        tasks.append(
            ExternalTask(
                name=spec["id"],
                brief=_OFFICEVAL_BRIEF.format(instruction=spec["instruction"]),
                inputs=inputs,
                grade=_officeval_grader(spec["id"], grader, python),
            )
        )
    return tasks


def _officeval_grader(task_id: str, grader: Path, python: str) -> Callable[[Path, Path], Any]:
    def grade(workspace: Path, task_out: Path) -> dict[str, Any]:
        originals = json.loads((task_out / "inputs.json").read_text(encoding="utf-8"))
        submission = task_out / "submission" / task_id
        if submission.exists():
            shutil.rmtree(submission)
        submission.mkdir(parents=True)
        for path in changed_files(workspace, originals, OFFICE_SUFFIXES):
            target = submission / path.relative_to(workspace)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        if not any(submission.iterdir()):
            # The benchmark scores a task with no deliverable as nothing, without its verifier.
            return {"submitted": [], "score_fraction": 0.0, "reason": "no Office file written"}
        verifier = grader / "verifiers" / f"{task_id}_verifier.py"
        code = (
            "import importlib.util, json, sys\n"
            "spec = importlib.util.spec_from_file_location('verifier', sys.argv[1])\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "print(json.dumps(module.evaluate(sys.argv[2]), ensure_ascii=False, default=str))\n"
        )
        report = _run_json([python, "-c", code, str(verifier), str(submission)], grader)
        report["submitted"] = sorted(str(p.relative_to(submission)) for p in submission.rglob("*"))
        report["score_fraction"] = officeval_fraction(report)
        return report

    return grade


def officeval_fraction(report: dict[str, Any]) -> float | None:
    """The benchmark's completion rate (`core/csv_reporter.py`): nothing when the structural check
    (dimension one) failed, else the points with a negative total counted as none."""
    if report.get("status") == "ok" and report.get("dim1_pass") is False:
        return 0.0
    total, maximum = report.get("total_score"), report.get("max_score")
    if isinstance(total, bool) or not isinstance(total, int | float):
        return None
    if isinstance(maximum, bool) or not isinstance(maximum, int | float) or maximum <= 0:
        return None
    return max(0.0, float(total)) / float(maximum)


def spreadsheet_tasks(
    data: Path, grader: Path, wanted: list[str], python: str
) -> list[ExternalTask]:
    entries = {str(e["id"]): e for e in json.loads((data / "dataset.json").read_text(encoding="utf-8"))}
    tasks = []
    for task_id in wanted:
        entry = entries[task_id]
        folder = data / entry["spreadsheet_path"]
        source = folder / f"1_{task_id}_init.xlsx"
        golden = folder / f"1_{task_id}_golden.xlsx"
        position = entry["answer_position"]
        if entry.get("answer_sheet") and "!" not in position:
            position = f"'{entry['answer_sheet']}'!{position}"
        tasks.append(
            ExternalTask(
                name=f"sb-{task_id}",
                brief=_SPREADSHEET_BRIEF.format(
                    name=source.name,
                    instruction=entry["instruction"],
                    kind=entry["instruction_type"],
                    position=position,
                ),
                inputs=[source],
                grade=_spreadsheet_grader(entry, golden, grader, python),
            )
        )
    return tasks


def _spreadsheet_grader(
    entry: dict[str, Any], golden: Path, grader: Path, python: str
) -> Callable[[Path, Path], Any]:
    def grade(workspace: Path, task_out: Path) -> dict[str, Any]:
        output = workspace / "output.xlsx"
        if not output.is_file():
            originals = json.loads((task_out / "inputs.json").read_text(encoding="utf-8"))
            changed = changed_files(workspace, originals, (".xlsx",))
            if not changed:
                return {"passed": False, "reason": "no workbook written", "score_fraction": 0.0}
            output = max(changed, key=lambda p: p.stat().st_mtime)
        recalculated = task_out / "graded.xlsx"
        recalculate(output, recalculated)
        code = (
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from evaluation import compare_workbooks\n"
            "ok, message = compare_workbooks(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])\n"
            "print(json.dumps({'passed': bool(ok), 'message': message}))\n"
        )
        report = _run_json(
            [
                python,
                "-c",
                code,
                str(grader / "evaluation"),
                str(golden),
                str(recalculated),
                entry["instruction_type"],
                entry["answer_position"],
            ],
            grader,
        )
        report["graded_file"] = output.name
        report["score_fraction"] = 1.0 if report.get("passed") else 0.0
        return report

    return grade


def recalculate(source: Path, target: Path) -> None:
    """Open `source` in LibreOffice and save it as `target`, so the formulas' values are cached
    for a reader of values: the benchmark's own recalculation step."""
    from coscribe.tools import find_libreoffice

    with tempfile.TemporaryDirectory() as folder:
        found = find_libreoffice(Path(folder))
        if found is None:
            raise RuntimeError("LibreOffice is needed to recalculate the workbook")
        soffice = found[0]
        profile = Path(folder) / "profile"
        work = Path(folder) / "in"
        work.mkdir()
        copy = work / "book.xlsx"
        shutil.copyfile(source, copy)
        out = Path(folder) / "out"
        subprocess.run(
            [
                str(soffice),
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--calc",
                "--convert-to",
                "xlsx:Calc MS Excel 2007 XML",
                "--outdir",
                str(out),
                str(copy),
            ],
            check=True,
            capture_output=True,
            timeout=GRADE_TIMEOUT,
        )
        shutil.copyfile(out / "book.xlsx", target)


def changed_files(
    workspace: Path, originals: dict[str, str], suffixes: tuple[str, ...]
) -> list[Path]:
    """Files of these kinds the agent made or changed: an input still byte-identical is not one."""
    import hashlib

    found = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in suffixes or path.name.startswith("~$"):
            continue
        relative = str(path.relative_to(workspace))
        if originals.get(relative) != hashlib.sha256(path.read_bytes()).hexdigest():
            found.append(path)
    return found


def _run_json(command: list[str], cwd: Path) -> dict[str, Any]:
    try:
        done = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=GRADE_TIMEOUT, check=False
        )
    except subprocess.TimeoutExpired:
        return {"grader_error": f"no result after {GRADE_TIMEOUT} s"}
    lines = done.stdout.strip().splitlines()
    try:
        return dict(json.loads(lines[-1]))
    except (IndexError, ValueError):
        return {"grader_error": (done.stderr or done.stdout)[-3000:]}


async def run_one(task: ExternalTask, out: Path, args: argparse.Namespace) -> dict[str, Any]:
    import hashlib

    task_out = out.resolve() / task.name
    if task_out.exists():
        shutil.rmtree(task_out)
    workspace = task_out / "workspace"
    workspace.mkdir(parents=True)
    originals = {}
    for source in task.inputs:
        shutil.copyfile(source, workspace / source.name)
        originals[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    (task_out / "inputs.json").write_text(json.dumps(originals, ensure_ascii=False), "utf-8")

    usage = base.Usage()
    base._CURRENT_USAGE.set(usage)  # noqa: SLF001
    recorder = base.Recorder()
    status, error = "ok", None
    started = time.monotonic()
    try:
        session = base._build_session(  # noqa: SLF001
            task_out, workspace, args.model, task.name, args.effort
        )
        recorder.session = session
        await asyncio.wait_for(session.handle_user_message(task.brief, recorder), args.timeout)
        if recorder.errors:
            status, error = "error", "; ".join(recorder.errors)
    except TimeoutError:
        status, error = "timeout", f"no end of turn after {args.timeout:.0f} s"
    except Exception as exc:  # noqa: BLE001 -- one task failing must not stop the run
        status, error = "error", f"{type(exc).__name__}: {exc}"
    wall = time.monotonic() - started
    result = {
        "task": task.name,
        "model": args.model,
        "effort": args.effort,
        "status": status,
        "error": error,
        "wall_seconds": round(wall, 1),
        "model_calls": usage.model_calls,
        "input_tokens": usage.input_tokens,
        "cached_tokens": usage.cached_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "cost": cost(args.model, usage.input_tokens, usage.cached_tokens, usage.output_tokens),
        "tool_calls": dict(recorder.tool_calls),
        "tool_errors": recorder.tool_errors,
        "questions_answered_for_the_user": recorder.questions,
        "messages": recorder.messages,
    }
    (task_out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    grade = await asyncio.to_thread(task.grade, workspace, task_out)
    (task_out / "grade.json").write_text(json.dumps(grade, ensure_ascii=False, indent=2), "utf-8")
    shutil.rmtree(task_out / "state" / "script-env", ignore_errors=True)
    return {**result, "score_fraction": grade.get("score_fraction")}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [r["score_fraction"] for r in rows if r["score_fraction"] is not None]
    costs = [r["cost"] for r in rows if r["cost"] is not None]
    return {
        "tasks": len(rows),
        "graded": len(scores),
        "mean_score": round(sum(scores) / len(scores), 4) if scores else None,
        "total_cost": round(sum(costs), 4),
        "cost_per_task": round(sum(costs) / len(costs), 4) if costs else None,
        "rows": [
            {
                k: r[k]
                for k in ("task", "status", "score_fraction", "cost", "wall_seconds", "model_calls")
            }
            for r in rows
        ],
    }


async def run_all(tasks: list[ExternalTask], args: argparse.Namespace) -> list[dict[str, Any]]:
    gate = asyncio.Semaphore(args.jobs)

    async def one(task: ExternalTask) -> dict[str, Any]:
        async with gate:
            print(f"start {task.name}", flush=True)
            row = await run_one(task, args.out, args)
            print(
                f"done  {task.name}: {row['status']}, score {row['score_fraction']}, "
                f"cost {row['cost']}, {row['wall_seconds']} s",
                flush=True,
            )
            return row

    return list(await asyncio.gather(*(one(t) for t in tasks)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--bench", choices=("officeval", "spreadsheetbench"), required=True)
    parser.add_argument("--data", type=Path, required=True, help="the benchmark's dataset")
    parser.add_argument("--grader", type=Path, required=True, help="the benchmark's repository")
    parser.add_argument("--tasks", required=True, help="comma-separated task ids")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=base.DEFAULT_MODEL)
    parser.add_argument("--effort", choices=base.EFFORT_LEVELS, default=base.DEFAULT_EFFORT)
    parser.add_argument("--timeout", type=float, default=base.DEFAULT_TIMEOUT)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument(
        "--grader-python", default=sys.executable, help="the interpreter the checker runs in"
    )
    args = parser.parse_args(argv)
    wanted = [t.strip() for t in args.tasks.split(",") if t.strip()]
    if args.bench == "officeval":
        skipped = sorted(OFFICEVAL_COM.intersection(wanted))
        if skipped and sys.platform != "win32":
            print(f"skip {', '.join(skipped)}: the checker needs Word on Windows", flush=True)
        wanted = [t for t in wanted if t not in OFFICEVAL_COM or sys.platform == "win32"]
        tasks = officeval_tasks(args.data, args.grader, wanted, args.grader_python)
    else:
        tasks = spreadsheet_tasks(args.data, args.grader, wanted, args.grader_python)
    args.out.mkdir(parents=True, exist_ok=True)
    with base.measured_models():
        rows = asyncio.run(run_all(tasks, args))
    summary = summarize(rows)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), "utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
