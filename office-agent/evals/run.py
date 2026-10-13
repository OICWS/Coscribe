"""Run evaluation tasks through coscribe's real agent and check what comes out.

    python -m evals.run --route current --tasks all --out evals/runs/baseline
    python -m evals.run --tasks 01,03 --out evals/runs/try
    python -m evals.run --check-only --out evals/runs/baseline    # re-check, no model calls
    python -m evals.run --kind xlsx --out evals/runs/excel        # the Excel tasks

Each task gets a fresh workspace holding its input files; its brief is sent as one user
message to a `ChatSessionLG` that acts without asking (the tier of a scheduled run), the
way the app builds one. A task's folder under `--out` holds `result.json` (usage, time, tool
calls), `checks.json`, the workspace and the rendered pages.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import contextvars
import json
import os
import shutil
import sys
import time
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .pptx_checks import check_deck
from .prices import cost
from .tasks import KINDS, Task, discover
from .xlsx_checks import check_workbook

DEFAULT_MODEL = "deepseek:deepseek-flash"
DEFAULT_EFFORT = "low"
DEFAULT_TIMEOUT = 1800.0
DEEPSEEK_URL = "https://api.deepseek.com/v1"
ROUTES = {"current": "coscribe's coordinator agent as it ships"}
# What a task of each kind produces and how it is checked.
SUFFIXES = {"pptx": ".pptx", "xlsx": ".xlsx", "docx": ".docx"}
CHECKERS = {"pptx": check_deck, "xlsx": check_workbook}
_ANSWER = "Decide it yourself, I am not available; continue with the task."


@dataclass
class Usage:
    model_calls: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    def add(self, metadata: dict[str, Any]) -> None:
        self.model_calls += 1
        self.input_tokens += metadata.get("input_tokens", 0)
        self.output_tokens += metadata.get("output_tokens", 0)
        self.cached_tokens += (metadata.get("input_token_details") or {}).get("cache_read", 0)
        self.reasoning_tokens += (metadata.get("output_token_details") or {}).get("reasoning", 0)


_CURRENT_USAGE: contextvars.ContextVar[Usage | None] = contextvars.ContextVar(
    "eval_usage", default=None
)


def _usage_callback(usage: Usage) -> Any:
    from langchain_core.callbacks import BaseCallbackHandler

    class Collect(BaseCallbackHandler):
        def on_llm_end(self, response: Any, **kwargs: Any) -> None:
            for generations in response.generations:
                for generation in generations:
                    metadata = getattr(getattr(generation, "message", None), "usage_metadata", None)
                    if metadata:
                        usage.add(metadata)

    return Collect()


@dataclass
class Recorder:
    """The client end of one conversation: records what happened and answers whatever would
    wait for a person."""

    session: Any = None
    can_resolve_approvals: bool = False
    tool_calls: Counter[str] = field(default_factory=Counter)
    tool_errors: list[str] = field(default_factory=list)
    questions: int = 0
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    async def send_json(self, data: dict[str, Any]) -> None:
        kind = data.get("type")
        if kind == "tool_started":
            name = data["tool_name"]
            inner = (data.get("arguments") or {}).get("name") if name == "use_tool" else None
            self.tool_calls[f"{name}:{inner}" if inner else name] += 1
        elif kind == "tool_result" and data.get("is_error"):
            self.tool_errors.append(f"{data['tool_name']}: {str(data.get('result'))[:300]}")
        elif kind == "question_required":
            self.questions += 1
            self.session.resolve_question(data["id"], [_ANSWER for _ in data["questions"]])
        elif kind == "plan_ready":
            self.questions += 1
            self.session.resolve_question(data["id"], _ANSWER)
        elif kind == "approval_required":
            self.session.resolve_approval(data["id"], True)
        elif kind == "agent_message":
            self.messages.append(data["text"])
        elif kind == "error":
            self.errors.append(str(data.get("message")))


def _build_session(root: Path, workspace: Path, model: str, thread_id: str) -> Any:
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.config import Settings
    from coscribe.conversation.session import ChatSessionLG
    from coscribe.runtime import empty_hooks_config
    from coscribe.runtime.llm_client import LLMClient
    from coscribe.tools.skill_catalog import enabled_skill_names

    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        default_model=model,
        workspace_root=workspace,
        state_dir=root / "state",
        skills_dir=root / "skills",
        custom_templates_dir=root / "templates",
        memory_path=root / "MEMORY.md",
        auto_title_threads=False,
    )
    providers = {"deepseek": {"base_url": DEEPSEEK_URL, "api_key": os.environ["DEEPSEEK_API_KEY"]}}
    session = ChatSessionLG(
        thread_id=thread_id,
        settings=settings,
        context_window_client=LLMClient(custom_providers=providers),
        custom_providers=providers,
        extra_tools=[],
        checkpointer=InMemorySaver(),
        hooks_config=empty_hooks_config(),
        enabled_skill_names=enabled_skill_names(settings.skills_dir, settings.state_dir),
        workspace_root=workspace,
    )
    # A scheduled run's tier: every gated call goes ahead, nobody is asked.
    session.run_approval_mode = "skip"
    return session


def _find_output(
    workspace: Path, originals: dict[str, bytes], messages: list[str], suffix: str
) -> Path | None:
    """The file of the task's kind the agent wrote or changed (an input still byte-identical is
    not one); when several qualify, the newest of those its own messages name, else the newest."""
    files = [
        p
        for p in workspace.rglob(f"*{suffix}")
        if originals.get(str(p.relative_to(workspace))) != p.read_bytes()
    ]
    said = "\n".join(messages)
    named = [p for p in files if p.name in said]
    return max(named or files, key=lambda p: p.stat().st_mtime, default=None)


@contextlib.contextmanager
def measured_models(effort: str | None) -> Iterator[None]:
    """Every model the sessions build reports its usage to the task that is running, and gets
    the reasoning effort. Installed once around the whole run: tasks overlap, so a patch made
    and undone per task would drop or leak another task's wrapper."""
    from coscribe.conversation import session as session_module

    original = session_module.resolve_chat_model

    def resolve(name: str, custom_providers: Any = None) -> Any:
        chat_model = original(name, custom_providers)
        collector = _CURRENT_USAGE.get()
        if collector is not None:
            chat_model.callbacks = [_usage_callback(collector)]
        if effort and hasattr(chat_model, "reasoning_effort"):
            chat_model.reasoning_effort = effort
        return chat_model

    session_module.resolve_chat_model = resolve
    try:
        yield
    finally:
        session_module.resolve_chat_model = original


async def run_task(
    task: Task, out: Path, model: str, effort: str | None, timeout: float
) -> dict[str, Any]:
    task_out = out / task.name
    if task_out.exists():
        shutil.rmtree(task_out)
    workspace = task_out / "workspace"
    workspace.mkdir(parents=True)
    originals: dict[str, bytes] = {}
    inputs_root = task.directory / "inputs"
    for source in task.inputs:
        relative = source.relative_to(inputs_root)
        (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, workspace / relative)
        originals[str(relative)] = source.read_bytes()

    usage = Usage()
    _CURRENT_USAGE.set(usage)
    recorder = Recorder()
    status, error = "ok", None
    started = time.monotonic()
    try:
        session = _build_session(task_out, workspace, model, task.name)
        recorder.session = session
        await asyncio.wait_for(session.handle_user_message(task.brief, recorder), timeout)
        if recorder.errors:
            status, error = "error", "; ".join(recorder.errors)
    except TimeoutError:
        status, error = "timeout", f"no end of turn after {timeout:.0f} s"
    except Exception as exc:  # noqa: BLE001 -- one task failing must not stop the run
        status, error = "error", f"{type(exc).__name__}: {exc}"
    wall = time.monotonic() - started

    output = _find_output(workspace, originals, recorder.messages, SUFFIXES[task.kind])
    result = {
        "task": task.name,
        "kind": task.kind,
        "route": "current",
        "model": model,
        "effort": effort,
        "status": status,
        "error": error,
        "wall_seconds": round(wall, 1),
        "model_calls": usage.model_calls,
        "input_tokens": usage.input_tokens,
        "cached_tokens": usage.cached_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "cost": cost(model, usage.input_tokens, usage.cached_tokens, usage.output_tokens),
        "tool_call_count": sum(recorder.tool_calls.values()),
        "tool_calls": dict(recorder.tool_calls),
        "tool_errors": recorder.tool_errors,
        "questions_answered_for_the_user": recorder.questions,
        "output": str(output.relative_to(workspace)) if output else None,
        "messages": recorder.messages,
    }
    (task_out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    check_task(task, task_out)
    return result


def check_task(task: Task, task_out: Path) -> dict[str, Any]:
    result = json.loads((task_out / "result.json").read_text(encoding="utf-8"))
    workspace = task_out / "workspace"
    output = result.get("output") or result.get("deck")  # `deck` in runs made before the kinds
    if output is None:
        report: dict[str, Any] = {
            "output": None,
            "opens": {"ok": False, "error": f"no {task.kind} file produced"},
        }
    else:
        report = CHECKERS[task.kind](task, workspace / output, workspace, task_out / "render")
    (task_out / "checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def _ok(report: dict[str, Any], check: str) -> bool | None:
    """Whether a check passed; None for a check this task does not ask for."""
    found = report.get(check)
    return None if found is None else bool(found.get("ok"))


def _matched(report: dict[str, Any], check: str) -> str | None:
    found = report.get(check)
    return None if found is None else f"{found['matched']}/{found['checked']}"


def _kind_columns(kind: str, report: dict[str, Any]) -> dict[str, Any]:
    if kind == "xlsx":
        recalc = report.get("recalc") or {}
        return {
            "recalc": recalc.get("ok", False),
            "formula_cells": recalc.get("formulas"),
            "errors": recalc.get("errors"),
            "cells": _matched(report, "cells"),
            "formulas": _ok(report, "formulas"),
            "constants": _ok(report, "constants"),
            "formats": _ok(report, "number_formats"),
            "styles_kept": _ok(report, "untouched"),
            "features_kept": _ok(report, "features"),
            "used_range": _ok(report, "used_range"),
            "probe": _ok(report, "probe"),
            "charts": _ok(report, "charts"),
            "validations": _ok(report, "validations"),
        }
    layout = report.get("layout") or {}
    return {
        "pages": (report.get("pages") or {}).get("count"),
        "pages_ok": (report.get("pages") or {}).get("ok", False),
        "editable": (report.get("editability") or {}).get("ok", False),
        "pictures_ok": (report.get("pictures") or {}).get("ok"),
        "template_kept": (report.get("template") or {}).get("ok"),
        "overflow": layout.get("overflow_words"),
        "overlaps": layout.get("text_overlaps"),
    }


# The summary table: the columns each kind shows, after `task`, `status` and `opens`.
SUMMARY_COLUMNS = {
    "pptx": ["facts", "pages", "editable", "inventions", "overflow", "overlaps"],
    "xlsx": [
        "recalc",
        "errors",
        "facts",
        "cells",
        "formulas",
        "constants",
        "formats",
        "styles_kept",
        "features_kept",
        "used_range",
        "probe",
        "charts",
        "validations",
        "inventions",
    ],
}


def summary_row(result: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    facts = report.get("facts") or {}
    return {
        "task": result["task"],
        "status": result["status"],
        "opens": report.get("opens", {}).get("ok", False),
        "facts": f"{facts.get('found', 0)}/{facts.get('total', 0)}",
        "inventions": (report.get("inventions") or {}).get("count"),
        **_kind_columns(result.get("kind", "pptx"), report),
        "seconds": result["wall_seconds"],
        "tool_calls": result["tool_call_count"],
        "input_tokens": result["input_tokens"],
        "cached_tokens": result["cached_tokens"],
        "output_tokens": result["output_tokens"],
        "cost": result["cost"],
    }


def write_summary(out: Path, tasks: list[Task], kind: str = "pptx") -> None:
    rows = []
    for task in tasks:
        folder = out / task.name
        if (folder / "result.json").is_file() and (folder / "checks.json").is_file():
            rows.append(
                summary_row(
                    json.loads((folder / "result.json").read_text(encoding="utf-8")),
                    json.loads((folder / "checks.json").read_text(encoding="utf-8")),
                )
            )
    (out / "summary.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    head = ["task", "status", "opens", *SUMMARY_COLUMNS[kind], "seconds", "tool_calls", "cost"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for row in rows:
        cells = [
            f"{row[h]:.4f}"
            if h == "cost" and row[h] is not None
            else "-"
            if row[h] is None
            else str(row[h])
            for h in head
        ]
        lines.append("| " + " | ".join(cells) + " |")
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_all(args: argparse.Namespace, tasks: list[Task], out: Path) -> None:
    gate = asyncio.Semaphore(args.jobs)

    async def one(task: Task) -> None:
        async with gate:
            print(f"start {task.name}", flush=True)
            # A dropped connection before the model answered once says nothing about the route.
            for _ in range(3):
                result = await run_task(task, out, args.model, args.effort, args.timeout)
                answered = result["model_calls"] or result["tool_call_count"] or result["messages"]
                if result["status"] != "error" or answered:
                    break
                print(f"retry {task.name}: {result['error']}", flush=True)
            print(
                f"done  {task.name}: {result['status']}, {result['wall_seconds']} s, "
                f"{result['tool_call_count']} tool calls, cost {result['cost']}",
                flush=True,
            )

    await asyncio.gather(*(one(t) for t in tasks))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--kind", choices=KINDS, default="pptx", help="which office tasks to run")
    parser.add_argument("--route", choices=sorted(ROUTES), default="current")
    parser.add_argument(
        "--tasks", default="all", help="`all`, or names / number prefixes, comma-separated"
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--effort", default=DEFAULT_EFFORT, help="reasoning effort; `none` leaves the default"
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds per task")
    parser.add_argument("--jobs", type=int, default=2, help="tasks run at the same time")
    parser.add_argument("--check-only", action="store_true", help="re-check an earlier run")
    args = parser.parse_args(argv)
    if args.effort == "none":
        args.effort = None
    tasks = discover(args.tasks, kind=args.kind)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        for task in tasks:
            if (out / task.name / "result.json").is_file():
                check_task(task, out / task.name)
    else:
        if "DEEPSEEK_API_KEY" not in os.environ:
            print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
            return 1
        with measured_models(args.effort):
            asyncio.run(run_all(args, tasks, out))
    write_summary(out, discover("all", kind=args.kind), args.kind)
    print((out / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
