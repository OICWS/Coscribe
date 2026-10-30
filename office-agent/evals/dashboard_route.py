"""Does a model make a working Dashboard from the person's data? (design note
`docs/assessments/2026-10-29-design-and-dashboard.md`, step 2.)

Six briefs, each with a data file in a throwaway workspace: four started from the Artifacts page's
Dashboard tile (the first-message note), two typed in an ordinary conversation. Each is sent to
coscribe's real agent with the built-in skills; the dashboard it leaves is read by the app's own
reader, its `data-figure` and `data-source` names are checked against its datasets, its figures
against the numbers the data gives, and the page is drawn in Chromium under the app's sandbox
policy for script errors and a screenshot. It calls a model, so it is run by hand, off-peak, and
is not part of CI; the checks are tested in `tests/test_evals_dashboard_route.py`.

    python -m evals.dashboard_route --out evals/runs/dashboard
    python -m evals.dashboard_route --tasks 01 --out evals/runs/try
    python -m evals.dashboard_route --check-only --out evals/runs/dashboard
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
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


def _csv(header: list[str], rows: list[list[Any]]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


_SCENARIOS = ["Follow", "Cut-in", "Cut-out", "Hard brake", "Stop & Go", "Curve", "Rain", "Night"]


def _test_runs() -> bytes:
    rows = []
    for day in range(1, 6):
        for i, scenario in enumerate(_SCENARIOS):
            failed = (i * 7 + day * 3) % 11 == 0 or (scenario == "Stop & Go" and day % 2 == 0)
            minutes = round(2 + (i * 1.3 + day * 0.7) % 5, 1)
            rows.append([f"2026-10-{20 + day}", scenario, "fail" if failed else "pass", minutes])
    return _csv(["date", "scenario", "result", "minutes"], rows)


def _sales() -> bytes:
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Sales"
    sheet.append(["Month", "North", "South", "East", "West"])
    for m, month in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun"]):
        sheet.append([month, 400 + m * 12, 300 + m * 3, 480 + m * 20, 290 - m * 6])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def _tickets() -> bytes:
    priorities = ["low", "normal", "high", "urgent"]
    tickets = [
        {
            "id": n,
            "priority": priorities[(n * 5) % 4],
            "status": "open" if n % 3 == 0 else "closed",
            "hours_to_close": None if n % 3 == 0 else (n * 7) % 40 + 2,
            "team": ["Billing", "Login", "Reports"][n % 3],
        }
        for n in range(1, 61)
    ]
    return json.dumps(tickets, indent=1).encode("utf-8")


def _traffic() -> bytes:
    rows = []
    for day in range(1, 29):
        for channel, base in (("search", 900), ("social", 400), ("email", 150)):
            visits = base + (day * 37 + len(channel) * 11) % 260
            rows.append([f"2026-09-{day:02d}", channel, visits])
    return _csv(["date", "channel", "visits"], rows)


def _budget() -> bytes:
    rows = [
        ["Venue", 4800, 5200],
        ["Travel", 4200, 3900],
        ["Food", 3000, 3350],
        ["Speakers", 2500, 2500],
        ["Print", 600, 410],
    ]
    return _csv(["line", "budget", "actual"], rows)


def _progress() -> bytes:
    rows = [
        ["需求评审", "张敏", "完成", 100],
        ["接口开发", "李强", "进行中", 60],
        ["前端页面", "王芳", "进行中", 45],
        ["测试用例", "李强", "未开始", 0],
        ["数据迁移", "张敏", "完成", 100],
        ["上线准备", "王芳", "未开始", 0],
    ]
    return _csv(["任务", "负责人", "状态", "完成度"], rows)


@dataclass
class Brief:
    name: str
    text: str
    # From the Dashboard tile (the note goes with the message) or typed in a conversation.
    from_tile: bool
    inputs: dict[str, Callable[[], bytes]] = field(default_factory=dict)
    # Numbers the page's figures should hold, each with a tolerance.
    figures: tuple[tuple[float, float], ...] = ()


BRIEFS = [
    Brief(
        "01-test-results",
        "Our ACC regression results for the week are in test_runs.csv. I want to see the pass "
        "rate, which scenarios fail most, and the failed runs.",
        True,
        {"test_runs.csv": _test_runs},
        ((40, 0.5),),
    ),
    Brief(
        "02-sales",
        "A dashboard of sales.xlsx: monthly sales per region (thousand USD), the total, and how "
        "each region is trending.",
        True,
        {"sales.xlsx": _sales},
        ((sum(400 + m * 12 + 300 + m * 3 + 480 + m * 20 + 290 - m * 6 for m in range(6)), 1),),
    ),
    Brief(
        "03-tickets",
        "tickets.json is our support queue. Show open tickets by priority and team, and the "
        "average hours to close.",
        True,
        {"tickets.json": _tickets},
        ((20, 0.5),),
    ),
    Brief(
        "04-traffic",
        "Make me a dashboard of September website visits from traffic.csv, by channel, with a "
        "way to look at one channel at a time.",
        False,
        {"traffic.csv": _traffic},
    ),
    Brief(
        "05-budget",
        "Build a dashboard comparing budget and actual spend per line in offsite_budget.csv, "
        "with the total over or under.",
        False,
        {"offsite_budget.csv": _budget},
        ((15100, 1), (15360, 1)),
    ),
    Brief(
        "06-progress-zh",
        "用 progress.csv 做一个项目进度看板：整体完成度、每个负责人的任务和状态。",
        True,
        {"progress.csv": _progress},
    ),
]

_MARKER = re.compile(r"<meta\s[^>]*coscribe[^>]*dashboard|<meta\s[^>]*dashboard[^>]*coscribe", re.I)
_ATTR = re.compile(r"""data-(figure|source)\s*=\s*["']([^"']+)["']""")
_SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b.*?</\1>", re.I | re.S)
_TAG = re.compile(r"<[^>]+>")
# A figure typed into the page: a number with at least three digits or a decimal part.
_TYPED = re.compile(r"(?<![\w#.-])\d[\d,]{2,}(?:\.\d+)?%?|(?<![\w#.-])\d+\.\d+%?")


def page_report(page: Path) -> dict[str, Any]:
    """A dashboard page as the app reads it, before it is drawn."""
    from coscribe.conversation.dashboard import DashboardDataError, read_dashboard_data

    source = page.read_text(encoding="utf-8", errors="replace")
    try:
        data = read_dashboard_data(page)
        data_error = None
    except DashboardDataError as exc:
        data, data_error = {"datasets": {}, "figures": {}}, str(exc)
    named = {"figure": set(data["figures"]), "source": set(data["datasets"])}
    unknown = sorted(
        {f"{kind}:{name}" for kind, name in _ATTR.findall(source) if name not in named[kind]}
    )
    text = _TAG.sub(" ", _SCRIPT_OR_STYLE.sub(" ", source))
    return {
        "datasets": {n: len(d.get("rows", [])) for n, d in data["datasets"].items()},
        "figures": {n: f.get("value") for n, f in data["figures"].items() if isinstance(f, dict)},
        "data_error": data_error,
        "unknown_names": unknown,
        "typed_numbers": sorted(
            {n.rstrip(",") for n in _TYPED.findall(text)} - {str(y) for y in range(1900, 2100)}
        )[:10],
        "sources_named": all(d.get("source") for d in data["datasets"].values()),
        "uses_d3": "data-coscribe-lib" in source,
    }


def figures_found(values: dict[str, Any], expected: tuple[tuple[float, float], ...]) -> list[bool]:
    """For each expected number, whether some figure holds it (a rate may be 0.4 or 40)."""
    numbers = [v for v in values.values() if isinstance(v, (int, float))]
    return [
        any(abs(v - want) <= tol or abs(v * 100 - want) <= tol for v in numbers)
        for want, tol in expected
    ]


_DRAW = r"""
const fs = require('fs'); const {chromium} = require('playwright');
(async () => {
  const [page, shot, policy] = process.argv.slice(1);
  const browser = await chromium.launch();
  const tab = await browser.newPage({viewport: {width: 1200, height: 900}});
  const errors = [];
  tab.on('pageerror', e => errors.push(e.message));
  tab.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await tab.route('http://dashboard.test/**', r => r.fulfill({status: 200, contentType: 'text/html',
    headers: {'Content-Security-Policy': policy}, body: fs.readFileSync(page)}));
  await tab.goto('http://dashboard.test/page');
  await tab.waitForTimeout(800);
  const marks = await tab.locator('svg rect, svg path, svg circle, svg line').count();
  const empty = await tab.locator('[data-figure]').evaluateAll(
    els => els.filter(e => !e.textContent.trim() || e.textContent.trim() === '—').length);
  await tab.screenshot({path: shot, fullPage: true});
  console.log(JSON.stringify({errors, marks, empty_figures: empty}));
  await browser.close();
})().catch(e => {
  console.log(JSON.stringify({errors: [String(e)], marks: 0, empty_figures: 0}));
});
"""


def draw(page: Path, shot: Path) -> dict[str, Any]:
    """The served page drawn in Chromium under the app's own sandbox policy."""
    from coscribe.conversation.dashboard import render_dashboard
    from coscribe.web.routes.design import _POLICY

    served = page.with_suffix(".served.html")
    served.write_bytes(render_dashboard(page, page.read_bytes()))
    try:
        done = subprocess.run(
            ["node", "-e", _DRAW, str(served), str(shot), _POLICY],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=page.parent,
        )
        result: dict[str, Any] = json.loads(done.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError) as exc:
        result = {"errors": [f"not drawn: {exc}"], "marks": 0, "empty_figures": 0}
    finally:
        served.unlink(missing_ok=True)
    return result


def judge(brief: Brief, workspace: Path, calls: dict[str, int]) -> dict[str, Any]:
    pages = sorted(
        p
        for p in workspace.rglob("*.html")
        if not p.name.endswith(".served.html")
        and _MARKER.search(p.read_text(encoding="utf-8", errors="replace")[:8192])
    )
    report: dict[str, Any] = {
        "skill_loaded": any(name.startswith("load_skill") for name in calls),
        "looked": sum(n for name, n in calls.items() if name.endswith("look_at_page")),
        "pages": [str(p.relative_to(workspace)) for p in pages],
        "made": bool(pages),
    }
    if not pages:
        report["ok"] = False
        return report
    page = pages[0]
    found = page_report(page)
    drawn = draw(page, workspace.parent / "screenshot.png")
    found["figures_right"] = figures_found(found["figures"], brief.figures)
    report.update(found)
    report.update(drawn)
    report["ok"] = bool(
        found["datasets"]
        and all(found["datasets"].values())
        and not found["data_error"]
        and not found["unknown_names"]
        and not drawn["errors"]
        and not drawn["empty_figures"]
        and all(found["figures_right"])
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
    for name, make in brief.inputs.items():
        (workspace / name).write_bytes(make())
    usage = Usage()
    _CURRENT_USAGE.set(usage)
    recorder = Recorder()
    status, error = "ok", None
    started = time.monotonic()
    try:
        session = _build_session(task_out, workspace, model, brief.name, effort)
        recorder.session = session
        artifact = "dashboard" if brief.from_tile else None
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
        "| task | tile | made | skill | looked | datasets | unknown | typed | errors | marks | figures | ok "
        "| cost |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        rows.append(
            f"| {r['task']} | {'yes' if r['from_tile'] else 'no'} | {'yes' if r['made'] else 'NO'} "
            f"| {'yes' if r['skill_loaded'] else 'no'} | {r.get('looked', 0)} "
            f"| {r.get('datasets', '')} "
            f"| {len(r.get('unknown_names', []))} | {len(r.get('typed_numbers', []))} "
            f"| {len(r.get('errors', []))} | {r.get('marks', '')} "
            f"| {r.get('figures_right', '')} | {'yes' if r['ok'] else 'NO'} "
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
