"""Does a model write a Doc when it should, and a valid one? (decision 0025, step 6.)

Fifteen briefs a user might type: seven for writing with no format named (or only what the person
will do with it), three that ask for Word by name, a template or tracked changes, two that want
an answer in chat, and three that ask to be explained something, one of them in a form to keep or
send (decision 0027: the AI decides when an explanation becomes a Doc). Each is sent to coscribe's
real agent with the built-in skills, in a throwaway workspace; the result is classified (a Doc, a
.docx, plain Markdown or nothing) and a Doc is read by the app's own parsers. It calls a model, so
it is run by hand, off-peak, and is not part of CI; only its deterministic parts are tested
(`tests/test_evals_doc_route.py`).

    python -m evals.doc_route --out evals/runs/doc-route
    python -m evals.doc_route --tasks 01,04 --out evals/runs/try
    python -m evals.doc_route --check-only --out evals/runs/doc-route
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import shutil
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .prices import cost
from .run import (
    _CURRENT_USAGE,
    DEFAULT_EFFORT,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    EFFORT_LEVELS,
    Recorder,
    Usage,
    _build_session,
    measured_models,
)


def _letter_template() -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph("ACME Corp, 1 Main Street")
    document.add_paragraph("[Date]")
    document.add_paragraph("[Recipient]")
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def _contract() -> bytes:
    from docx import Document

    document = Document()
    document.add_heading("Service agreement", level=1)
    document.add_paragraph("Payment is due within 60 days of the invoice date.")
    document.add_paragraph("Either party may end this agreement with 30 days notice.")
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


@dataclass(frozen=True)
class Brief:
    name: str
    text: str
    expect: str  # "doc", "docx" or "chat"
    facts: tuple[str, ...] = ()
    inputs: dict[str, Callable[[], bytes]] = field(default_factory=dict)


BRIEFS = [
    Brief(
        "01-proposal",
        "Write a short proposal for moving our team wiki from Confluence to Notion. Facts: 40 "
        "people use it, migration takes 3 weeks, it costs 4,800 USD a year against 7,200 now, "
        "the decision is due on 15 March.",
        "doc",
        ("40 people", "3 weeks", "4,800", "7,200", "15 March"),
    ),
    Brief(
        "02-resume",
        "I need a resume for Lin Wei: 6 years as a data analyst at Northwind (2019-2025), SQL, "
        "Python and Tableau, MSc Statistics from Fudan University in 2018. It is for a job "
        "application I will submit online.",
        "doc",
        ("Lin Wei", "Northwind", "Fudan"),
    ),
    Brief(
        "03-guide",
        "Write a user guide for our new expense app. Steps: 1 scan the receipt, 2 pick a "
        "category, 3 submit, 4 wait for approval (about 2 days). Warn that receipts older than "
        "30 days are rejected. I will print it for the office.",
        "doc",
        ("receipt", "category", "30 days"),
    ),
    Brief(
        "04-report-chart",
        "Write the Q3 sales report with a table and a chart of sales by region. North 420, "
        "South 310, East 515, West 275 (thousand USD). East is the best region, West needs "
        "attention.",
        "doc",
        ("420", "310", "515", "275", "East", "West"),
    ),
    Brief(
        "05-letter",
        "Write a letter to my landlord Mr Evans asking him to repair the heating in flat 4B, "
        "broken since 2 January. I will send it by email.",
        "doc",
        ("Evans", "4B", "2 January"),
    ),
    Brief(
        "06-minutes-zh",
        "写一份会议纪要：周三产品评审会，参会人 张敏、李强、王芳；决定 4 月 10 日发布 2.0 版本；"
        "李强负责测试，4 月 5 日前完成；王芳负责发布说明。",
        "doc",
        ("张敏", "4 月 10 日", "李强", "王芳"),
    ),
    Brief(
        "07-handbook",
        "Prepare a one-page handbook for new hires: work hours 9 to 18, laptop collected from IT "
        "on day one, buddy assigned in week one, first review after 90 days.",
        "doc",
        ("9", "laptop", "buddy", "90 days"),
    ),
    Brief(
        "08-word-explicit",
        "Create a Word document report.docx summarizing: revenue 1.2M, costs 0.8M, profit 0.4M "
        "for 2024.",
        "docx",
        ("1.2M", "0.8M", "0.4M"),
    ),
    Brief(
        "09-template",
        "Write a letter to Ms Park confirming her interview on 3 May at 10:00, using "
        "letterhead.docx as the template.",
        "docx",
        ("Park", "3 May", "10:00"),
        {"letterhead.docx": _letter_template},
    ),
    Brief(
        "10-tracked",
        "In contract.docx change the payment term from 60 to 30 days. Use tracked changes so I "
        "can review it.",
        "docx",
        ("30 days",),
        {"contract.docx": _contract},
    ),
    Brief(
        "11-question",
        "In two sentences, what is the difference between gross margin and net margin?",
        "chat",
    ),
    Brief(
        "12-compare",
        "Compare Python and Go for a small web service in a short table, a few rows.",
        "chat",
    ),
    Brief(
        "13-explain-steps",
        "Explain how OAuth 2.0 with PKCE works, step by step. I am just trying to understand it.",
        "chat",
    ),
    Brief(
        "14-explain-to-share",
        "Our team offsite has a budget of 12,000 USD for 20 people. Explain how we could split "
        "it between venue, travel and food, in a form I can send to the team afterwards.",
        "doc",
        ("12,000", "20"),
    ),
    Brief(
        "15-explain-reread",
        "Walk me through how a 300,000 USD loan at 4% over 25 years is paid off: the monthly "
        "payment, what the first three years look like, and the total interest. I want to keep "
        "it and come back to it.",
        "doc",
        ("300,000", "25"),
    ),
]


def classify(workspace: Path, originals: dict[str, bytes]) -> dict[str, Any]:
    """What the agent left in the workspace: files it made or changed, by kind."""
    from coscribe.tools.office.doc import is_doc

    docs: list[str] = []
    plain: list[str] = []
    words: list[str] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or "versions" in path.parts:
            continue
        relative = str(path.relative_to(workspace))
        if originals.get(relative) == path.read_bytes():
            continue
        if path.suffix.lower() == ".docx":
            words.append(relative)
        elif path.suffix.lower() == ".md":
            try:
                marked = is_doc(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                marked = False
            (docs if marked else plain).append(relative)
    got = "doc" if docs else "docx" if words else "plain_md" if plain else "none"
    return {"got": got, "docs": docs, "docx": words, "plain_md": plain}


def doc_report(source: str, facts: tuple[str, ...]) -> dict[str, Any]:
    """A Doc as the app reads it: its blocks, the ones it cannot show as such, a chart that does not
    parse, and the facts the brief gave that are missing."""
    from coscribe.tools.office.doc import parse_chart, read_doc

    blocks = read_doc(source).blocks
    bad_charts = []
    for block in blocks:
        if block.kind == "chart":
            try:
                parse_chart(block.text)
            except ValueError as error:
                bad_charts.append(str(error))
    lowered = source.lower()
    return {
        "blocks": dict(Counter(b.kind for b in blocks)),
        "raw_blocks": [b.kind for b in blocks if b.kind in ("html", "other")],
        "bad_charts": bad_charts,
        "missing_facts": [f for f in facts if f.lower() not in lowered],
    }


def judge(
    brief: Brief, workspace: Path, originals: dict[str, bytes], calls: dict[str, int]
) -> dict[str, Any]:
    found = classify(workspace, originals)
    # A chat answer leaves no file behind.
    wanted = "none" if brief.expect == "chat" else brief.expect
    report: dict[str, Any] = {**found, "route_ok": found["got"] == wanted}
    report["skill_loaded"] = any(name.startswith("load_skill") for name in calls)
    if found["got"] == "doc":
        source = (workspace / found["docs"][0]).read_text(encoding="utf-8")
        report["doc"] = doc_report(source, brief.facts)
        d = report["doc"]
        report["valid"] = not (d["raw_blocks"] or d["bad_charts"] or d["missing_facts"])
    return report


async def run_brief(
    brief: Brief, out: Path, model: str, effort: str, timeout: float
) -> dict[str, Any]:
    task_out = out.resolve() / brief.name
    if task_out.exists():
        shutil.rmtree(task_out)
    workspace = task_out / "workspace"
    workspace.mkdir(parents=True)
    originals: dict[str, bytes] = {}
    for name, make in brief.inputs.items():
        data = make()
        (workspace / name).write_bytes(data)
        originals[name] = data
    usage = Usage()
    _CURRENT_USAGE.set(usage)
    recorder = Recorder()
    status, error = "ok", None
    started = time.monotonic()
    try:
        session = _build_session(task_out, workspace, model, brief.name, effort)
        recorder.session = session
        await asyncio.wait_for(session.handle_user_message(brief.text, recorder), timeout)
        if recorder.errors:
            status, error = "error", "; ".join(recorder.errors)
    except TimeoutError:
        status, error = "timeout", f"no end of turn after {timeout:.0f} s"
    except Exception as exc:  # noqa: BLE001 -- one brief failing must not stop the run
        status, error = "error", f"{type(exc).__name__}: {exc}"
    result = {
        "task": brief.name,
        "expect": brief.expect,
        "status": status,
        "error": error,
        "wall_seconds": round(time.monotonic() - started, 1),
        "model_calls": usage.model_calls,
        "cost": cost(model, usage.input_tokens, usage.cached_tokens, usage.output_tokens),
        "tool_calls": dict(recorder.tool_calls),
        "tool_errors": recorder.tool_errors,
        "messages": recorder.messages,
        **judge(brief, workspace, originals, dict(recorder.tool_calls)),
    }
    (task_out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.rmtree(task_out / "state" / "script-env", ignore_errors=True)
    return result


def summary(results: list[dict[str, Any]]) -> str:
    rows = [
        "| task | expect | got | route | skill | valid | cost | calls |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        valid = r.get("valid", "")
        rows.append(
            f"| {r['task']} | {r['expect']} | {r['got']} | {'yes' if r['route_ok'] else 'NO'} "
            f"| {'yes' if r['skill_loaded'] else 'no'} | {valid} | {r['cost'] or 0:.3f} "
            f"| {r['model_calls']} |"
        )
    right = sum(1 for r in results if r["route_ok"])
    docs = [r for r in results if r["expect"] == "doc"]
    total = sum(r["cost"] or 0 for r in results)
    rows.append("")
    rows.append(
        f"Route right: {right}/{len(results)}; Doc chosen when it should be: "
        f"{sum(r['got'] == 'doc' for r in docs)}/{len(docs)}; valid Docs: "
        f"{sum(bool(r.get('valid')) for r in results)}; cost {total:.2f} USD."
    )
    return "\n".join(rows)


async def run_all(briefs: list[Brief], args: argparse.Namespace) -> list[dict[str, Any]]:
    gate = asyncio.Semaphore(args.jobs)

    async def one(brief: Brief) -> dict[str, Any]:
        async with gate:
            return await run_brief(brief, args.out, args.model, args.effort, args.timeout)

    results: list[dict[str, Any]] = await asyncio.gather(*(one(b) for b in briefs))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="all", help="`all`, or number prefixes, comma-separated")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", choices=EFFORT_LEVELS, default=DEFAULT_EFFORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--check-only", action="store_true", help="re-judge an earlier run")
    args = parser.parse_args(argv)
    wanted = None if args.tasks == "all" else args.tasks.split(",")
    briefs = [b for b in BRIEFS if wanted is None or any(b.name.startswith(w) for w in wanted)]
    args.out.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        results = []
        for b in briefs:
            folder = args.out / b.name
            if (folder / "result.json").is_file():
                previous = json.loads((folder / "result.json").read_text(encoding="utf-8"))
                originals = {n: (folder / "workspace" / n).read_bytes() for n in b.inputs}
                calls = previous.get("tool_calls", {})
                judged = judge(b, folder / "workspace", originals, calls)
                results.append({**previous, **judged})
    else:
        if "DEEPSEEK_API_KEY" not in os.environ:
            print("DEEPSEEK_API_KEY is not set", file=sys.stderr)
            return 1
        with measured_models():
            results = asyncio.run(run_all(briefs, args))
    text = summary(results)
    (args.out / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
