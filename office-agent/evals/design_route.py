"""Does a model make a working Design canvas? (design note
`docs/assessments/2026-10-29-design-and-dashboard.md`, step 5.)

Six briefs in a throwaway workspace: four started from the Artifacts page's Design tile (the
first-message note), two typed in an ordinary conversation. Each is sent to coscribe's real agent
with the built-in skills; the canvas it leaves is read by the app's own reader, its boards' pages
and variables are checked, and every artboard is drawn in Chromium at its own size, with the
canvas's variables put in as the app serves it and under the app's sandbox policy, for script
errors, blocked loads, overflow and a screenshot. It calls a model, so it is run by hand,
off-peak, and is not part of CI; the checks are tested in `tests/test_evals_design_route.py`.

    python -m evals.design_route --out evals/runs/design
    python -m evals.design_route --tasks 01 --out evals/runs/try
    python -m evals.design_route --check-only --out evals/runs/design
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
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


@dataclass
class Brief:
    name: str
    text: str
    # From the Design tile (the note goes with the message) or typed in a conversation.
    from_tile: bool
    # The fewest artboards the brief asks for.
    boards: int


BRIEFS = [
    Brief(
        "01-landing",
        "A landing page for Fieldnote, a notes app for field engineers that works offline. "
        "Desktop and phone versions.",
        True,
        2,
    ),
    Brief(
        "02-logo-options",
        "Three logo options for Leaf & Kettle, a small tea shop. Warm, simple, works on a cup.",
        True,
        1,
    ),
    Brief(
        "03-poster",
        "An A4 poster for our internal ADAS Safety Day on 12 November, 9:00-17:00, building C, "
        "with talks, a demo track and a test-drive slot sign-up.",
        True,
        1,
    ),
    Brief(
        "04-social",
        "Design three different square social posts announcing that our bike rental now has "
        "electric bikes, from 2 euros an hour.",
        False,
        3,
    ),
    Brief(
        "05-onboarding",
        "Make a design of a three-screen onboarding for a habit tracker phone app: welcome, pick "
        "habits, set a reminder.",
        False,
        3,
    ),
    Brief(
        "06-launch-zh",
        "为我们的新品发布会做一套设计：一张 A4 海报和一张朋友圈方图。"
        "产品是一款家用咖啡机，名叫“晨光”。",
        True,
        2,
    ),
]

_VAR_USE = re.compile(r"var\(\s*(--[\w-]+)")
_VAR_DEF = re.compile(r"(--[\w-]+)\s*:")


def canvas_report(canvas: Path) -> dict[str, Any]:
    """A canvas as the app reads it, before it is drawn: its boards, whether each page exists,
    its variables and which variables the pages use without anyone declaring them."""
    from coscribe.conversation import CanvasError, canvas_folder, read_canvas

    try:
        parsed = read_canvas(canvas)
    except CanvasError as exc:
        return {"canvas_error": str(exc), "boards": [], "variables": [], "undeclared": []}
    folder = canvas_folder(canvas)
    declared = {v["name"] for v in parsed["variables"]}
    boards, undeclared, used = [], set(), set()
    for board in parsed["boards"]:
        page = folder / board["file"]
        source = page.read_text(encoding="utf-8", errors="replace") if page.is_file() else ""
        uses = set(_VAR_USE.findall(source))
        used |= uses & declared
        undeclared |= uses - declared - set(_VAR_DEF.findall(source))
        boards.append({**board, "exists": page.is_file()})
    return {
        "canvas_error": None,
        "boards": boards,
        "variables": sorted(declared),
        "variables_used": sorted(used),
        "undeclared": sorted(undeclared),
    }


_DRAW = r"""
const fs = require('fs'); const {chromium} = require('playwright');
(async () => {
  const [page, shot, policy, width, height] = process.argv.slice(1);
  const browser = await chromium.launch();
  const tab = await browser.newPage({viewport: {width: +width, height: +height}});
  const errors = [];
  tab.on('pageerror', e => errors.push(e.message));
  tab.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await tab.route('http://design.test/**', r => r.fulfill({status: 200, contentType: 'text/html',
    headers: {'Content-Security-Policy': policy}, body: fs.readFileSync(page)}));
  await tab.goto('http://design.test/page');
  await tab.waitForTimeout(500);
  const size = await tab.evaluate(() => ({w: document.documentElement.scrollWidth,
    h: document.documentElement.scrollHeight}));
  await tab.screenshot({path: shot});
  console.log(JSON.stringify({errors, overflow_x: size.w > +width + 2, height: size.h}));
  await browser.close();
})().catch(e => {
  console.log(JSON.stringify({errors: [String(e)], overflow_x: false, height: 0}));
});
"""


def draw(page: Path, width: float, height: float, shot: Path) -> dict[str, Any]:
    """An artboard's page as the app serves it, drawn at the board's size under its policy."""
    from coscribe.web.routes.design import _POLICY, _with_canvas_variables

    served = page.with_suffix(".served.html")
    served.write_bytes(_with_canvas_variables(page, page.read_bytes()))
    try:
        done = subprocess.run(
            [
                "node",
                "-e",
                _DRAW,
                str(served),
                str(shot),
                _POLICY,
                str(int(width)),
                str(int(height)),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=page.parent,
        )
        result: dict[str, Any] = json.loads(done.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        result = {"errors": [f"not drawn: {exc}"], "overflow_x": False, "height": 0}
    finally:
        served.unlink(missing_ok=True)
    return result


def judge(brief: Brief, workspace: Path, calls: dict[str, int]) -> dict[str, Any]:
    from coscribe.conversation import canvas_folder

    canvases = sorted(workspace.rglob("*.design.json"))
    report: dict[str, Any] = {
        "skill_loaded": any(name.startswith("load_skill") for name in calls),
        "canvases": [str(c.relative_to(workspace)) for c in canvases],
        "loose_html": sorted(
            str(p.relative_to(workspace))
            for p in workspace.rglob("*.html")
            if not p.parent.name.endswith(".design") and not p.name.endswith(".served.html")
        ),
        "made": bool(canvases),
    }
    if not canvases:
        report["ok"] = False
        return report
    canvas = canvases[0]
    found = canvas_report(canvas)
    shots = workspace.parent / "screenshots"
    shots.mkdir(exist_ok=True)
    drawn = {}
    for board in found["boards"]:
        if board["exists"]:
            page = canvas_folder(canvas) / board["file"]
            shot = shots / f"{board['id']}.png"
            drawn[board["id"]] = draw(page, board["width"], board["height"], shot)
    report.update(found)
    report["drawn"] = drawn
    report["ok"] = bool(
        not found["canvas_error"]
        and len(found["boards"]) >= brief.boards
        and all(b["exists"] for b in found["boards"])
        and found["variables_used"]
        and not found["undeclared"]
        and not any(d["errors"] or d["overflow_x"] for d in drawn.values())
    )
    return report


async def run_brief(
    brief: Brief, out: Path, model: str, effort: str, timeout: float
) -> dict[str, Any]:
    task_out = out.resolve() / brief.name
    if task_out.exists():
        shutil.rmtree(task_out)
    workspace = task_out / "workspace"
    workspace.mkdir(parents=True)
    usage = Usage()
    _CURRENT_USAGE.set(usage)
    recorder = Recorder()
    status, error = "ok", None
    started = time.monotonic()
    try:
        session = _build_session(task_out, workspace, model, brief.name, effort)
        recorder.session = session
        artifact = "design" if brief.from_tile else None
        await asyncio.wait_for(
            session.handle_user_message(brief.text, recorder, artifact=artifact), timeout
        )
        if recorder.errors:
            status, error = "error", "; ".join(recorder.errors)
    except TimeoutError:
        status, error = "timeout", f"no end of turn after {timeout:.0f} s"
    except Exception as exc:  # noqa: BLE001 -- one brief failing must not stop the run
        status, error = "error", f"{type(exc).__name__}: {exc}"
    result = {
        "task": brief.name,
        "from_tile": brief.from_tile,
        "status": status,
        "error": error,
        "wall_seconds": round(time.monotonic() - started, 1),
        "model_calls": usage.model_calls,
        "cost": cost(model, usage.input_tokens, usage.cached_tokens, usage.output_tokens),
        "tool_calls": dict(recorder.tool_calls),
        "tool_errors": recorder.tool_errors,
        "messages": recorder.messages,
        **judge(brief, workspace, dict(recorder.tool_calls)),
    }
    (task_out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.rmtree(task_out / "state" / "script-env", ignore_errors=True)
    return result


def summary(results: list[dict[str, Any]]) -> str:
    rows = [
        "| task | tile | made | skill | boards | variables | undeclared | errors | overflow | ok "
        "| cost |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        drawn = r.get("drawn", {}).values()
        rows.append(
            f"| {r['task']} | {'yes' if r['from_tile'] else 'no'} | {'yes' if r['made'] else 'NO'} "
            f"| {'yes' if r['skill_loaded'] else 'no'} | {len(r.get('boards', []))} "
            f"| {len(r.get('variables_used', []))}/{len(r.get('variables', []))} "
            f"| {len(r.get('undeclared', []))} | {sum(len(d['errors']) for d in drawn)} "
            f"| {sum(d['overflow_x'] for d in drawn)} | {'yes' if r['ok'] else 'NO'} "
            f"| {r['cost'] or 0:.3f} |"
        )
    total = sum(r["cost"] or 0 for r in results)
    rows.append("")
    rows.append(
        f"Made: {sum(r['made'] for r in results)}/{len(results)}; working: "
        f"{sum(r['ok'] for r in results)}; cost {total:.2f} USD."
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
    parser.add_argument("--jobs", type=int, default=3)
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
                judged = judge(b, folder / "workspace", previous.get("tool_calls", {}))
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
