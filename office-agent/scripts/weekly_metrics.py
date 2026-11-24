#!/usr/bin/env python3
"""The weekly metrics page (`docs/metrics/<week>.md`): how the week's changes went.

    python scripts/weekly_metrics.py                   # this ISO week so far, to stdout
    python scripts/weekly_metrics.py --week 2026-W42 --write

Lead time and size of merged pull requests, reverts, how long `main` was red, runs that needed a
second attempt, how much of the suite the week's pull requests ran (decision 0059) and whether
the nightly selection audit stayed green, the core and component size budgets, the component
cards that the most commits have passed since they were last changed, how the ratchet baseline
moved and how many "Not verified" items the log holds. It reads GitHub through `gh api` (REST)
and the checkout through `git` (a shallow clone has no baseline from the week's start, and the
ratchet table then says n/a); it changes nothing but the page it writes.
`.github/workflows/weekly-numbers.yml` runs it every Monday for the week before and keeps the
body of the "Weekly numbers" issue current.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "docs" / "log"
LEDGER_FROM = "2026-10-08"
CI_WORKFLOW = ".github/workflows/office-agent-ci.yml"
BASELINE = "office-agent/quality/baseline.json"
AUDIT_WORKFLOW = ".github/workflows/test-selection-audit.yml"
BUDGET_WARN = 0.8  # a share of a budget worth naming before it fails
CARDS_LISTED = 5


def week_bounds(week: str) -> tuple[datetime, datetime]:
    """Monday 00:00 UTC to the next Monday, for an ISO week like `2026-W42`."""
    year, number = week.split("-W")
    start = datetime.fromisocalendar(int(year), int(number), 1).replace(tzinfo=UTC)
    return start, start + timedelta(days=7)


def parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def hours(delta: timedelta) -> float:
    return round(delta.total_seconds() / 3600, 1)


def red_time(runs: list[dict[str, Any]], start: datetime, end: datetime) -> timedelta:
    """Time `main` was red: from a failed run to the next green one (or the end of the window).

    `runs` are the CI runs of main with `created_at`, `updated_at` and `conclusion`."""
    ordered = sorted(
        (r for r in runs if r["conclusion"] in ("success", "failure")),
        key=lambda r: r["created_at"],
    )
    red_since: datetime | None = None
    total = timedelta()
    for run in ordered:
        if run["conclusion"] == "failure" and red_since is None:
            red_since = max(parse_time(run["created_at"]), start)
        elif run["conclusion"] == "success" and red_since is not None:
            total += max(min(parse_time(run["updated_at"]), end) - red_since, timedelta())
            red_since = None
    if red_since is not None:
        total += max(end - red_since, timedelta())
    return total


def ledger(log_dir: Path = LOG, since: str = LEDGER_FROM) -> dict[str, int]:
    """Entries of `docs/log/` since `since` and how many carry a "Not verified" item."""
    entries = items = 0
    for path in sorted(log_dir.glob("2026-*.md")):
        if path.name[:10] < since:
            continue
        entries += 1
        match = re.search(
            r"^## Not verified *\n(.*?)(?=^## |\Z)", path.read_text(encoding="utf-8"), re.S | re.M
        )
        body = match.group(1).strip() if match else ""
        if body and not body.lower().startswith(("- none", "none", "nothing")):
            items += 1
    return {"entries": entries, "with_not_verified": items}


def ratchet_trend(
    before: dict[str, dict[str, int]] | None, after: dict[str, dict[str, int]]
) -> list[str]:
    """One row per metric; `before` is None when the checkout has no history that far back."""
    lines = []
    for metric in sorted(set(before or {}) | set(after)):
        new = len(after.get(metric, {}))
        if before is None:
            lines.append(f"| {metric} | n/a | {new} | n/a |")
            continue
        old = len(before.get(metric, {}))
        lines.append(f"| {metric} | {old} | {new} | {new - old:+d} |")
    return lines


def selection(
    changes: Iterable[list[str]], plan: Callable[[list[str]], tuple[str, list[str]]], total: int
) -> list[str]:
    """How much of the suite each pull request's change selects, by test files.

    `plan` is `ci_scope.plan`: a `full` scope runs every test file, `docs` a handful."""
    scopes = {"docs": 0, "selected": 0, "full": 0}
    shares = []
    for files in changes:
        scope, tests = plan(files)
        scopes[scope] += 1
        shares.append(1.0 if scope == "full" else len(tests) / total)
    if not shares:
        return ["- no merged pull request this week"]
    return [
        f"- scope of the {len(shares)} merged pull requests: {scopes['selected']} selected, "
        f"{scopes['full']} full, {scopes['docs']} docs only",
        f"- share of the {total} test files they ran: mean {statistics.mean(shares):.0%}, "
        f"median {statistics.median(shares):.0%}",
    ]


def audit_line(runs: list[dict[str, Any]]) -> str:
    done = [r for r in runs if r["conclusion"] in ("success", "failure")]
    failed = sum(1 for r in done if r["conclusion"] == "failure")
    if not done:
        return "- nightly selection audit: no run this week"
    verdict = "a test that fails was not selected" if failed else "no miss"
    return f"- nightly selection audit: {len(done)} runs, {failed} failed ({verdict})"


def budget_lines(budgets: dict[str, int], sizes: dict[str, int], core: frozenset[str]) -> list[str]:
    total = sum(size for name, size in sizes.items() if name in core)
    largest = max(sizes, key=lambda name: sizes[name])
    limit = budgets["component_lines"]
    lines = [
        f"- core: {total} of {budgets['core_lines']} lines ({total / budgets['core_lines']:.0%})",
        f"- largest component: {largest}, {sizes[largest]} of {limit} lines",
    ]
    near = sorted((n for n, s in sizes.items() if s >= BUDGET_WARN * limit), key=lambda n: sizes[n])
    for name in reversed(near):
        lines.append(f"- near its budget: {name} ({sizes[name]} lines, {sizes[name] / limit:.0%})")
    return lines


def card_lines(behind: dict[str, int], listed: int = CARDS_LISTED) -> list[str]:
    """`behind`: component -> commits to its code since its card last changed."""
    ranked = sorted(behind.items(), key=lambda item: (-item[1], item[0]))[:listed]
    if not ranked or ranked[0][1] == 0:
        return ["- every card changed with its code's latest commit"]
    return [f"- {name}: {count} commits since its card changed" for name, count in ranked if count]


def render(
    week: str,
    merged: list[dict[str, Any]],
    red: timedelta,
    reruns: int,
    trend: list[str],
    notes: dict[str, int],
    scale: list[str] | None = None,
) -> str:
    lead = [hours(parse_time(p["merged_at"]) - parse_time(p["created_at"])) for p in merged]
    size = [p["additions"] + p["deletions"] for p in merged]
    reverts = [p for p in merged if re.match(r"(?i)\[?revert", p["title"])]
    out = [
        f"# Metrics {week}",
        "",
        "Written by `office-agent/scripts/weekly_metrics.py`; numbers are for the ISO week, UTC.",
        "",
        "## Pull requests",
        f"- merged: {len(merged)}",
    ]
    if merged:
        out += [
            f"- lead time (opened to merged): median {statistics.median(lead)} h, "
            f"longest {max(lead)} h",
            f"- size (lines added plus removed): median {int(statistics.median(size))}, "
            f"largest {max(size)}",
        ]
    out += [f"- reverts: {len(reverts)}", "", "## CI", f"- `main` was red for {hours(red)} h"]
    out += [f"- runs that needed a second attempt: {reruns}", ""]
    out += [*(scale or []), "## Ratchet", ""]
    out += ["| metric | names at week start | at week end | change |", "|---|---|---|---|"]
    out += trend or ["| (no baseline) | | | |"]
    out += [
        "",
        "## Not verified ledger",
        f"- log entries since {LEDGER_FROM}: {notes['entries']}, "
        f'{notes["with_not_verified"]} with a "Not verified" item',
        "",
    ]
    return "\n".join(out)


def _api(path: str, *extra: str) -> Any:
    out = subprocess.run(
        ["gh", "api", path, *extra], capture_output=True, text=True, check=True
    ).stdout
    return json.loads(out)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


def _repo() -> str:
    url = _git("remote", "get-url", "origin").strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url)
    if not match:
        raise SystemExit(f"cannot read OWNER/NAME from {url!r}")
    return match.group(1)


def _baseline_at(moment: datetime) -> dict[str, dict[str, int]] | None:
    commit = _git("rev-list", "-1", f"--before={moment.isoformat()}", "origin/main").strip()
    if not commit:
        return None
    try:
        loaded: dict[str, dict[str, int]] = json.loads(_git("show", f"{commit}:{BASELINE}"))
    except subprocess.CalledProcessError:
        return None
    return loaded


def _cards_behind(components: list[dict[str, Any]]) -> dict[str, int]:
    behind = {}
    for component in components:
        card = component.get("card")
        if not card:
            continue
        since = _git("log", "-1", "--format=%H", "origin/main", "--", card).strip()
        if not since:
            continue
        commits = _git(
            "rev-list", "--count", f"{since}..origin/main", "--", component["path"], f":!{card}"
        )
        behind[component["name"]] = int(commits.strip() or 0)
    return behind


def scale_sections(
    repo: str, merged: list[dict[str, Any]], audit_runs: list[dict[str, Any]]
) -> list[str]:
    """Selection, budgets and cards: the numbers that say whether the tree can keep growing."""
    scripts = str(Path(__file__).resolve().parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import ci_scope
    import ratchet

    graph = ci_scope.Graph.build(ci_scope.ROOT)
    changes = []
    for pull in merged:
        files: list[str] = []
        for page in range(1, 31):
            batch = _api(f"repos/{repo}/pulls/{pull['number']}/files?per_page=100&page={page}")
            files += [f["filename"] for f in batch]
            if len(batch) < 100:
                break
        changes.append(files)
    budgets = json.loads(ratchet.BUDGETS.read_text(encoding="utf-8"))
    components = tomllib.loads(ratchet.COMPONENTS.read_text("utf-8")).get("component", [])
    return [
        "## Test selection",
        *selection(changes, lambda files: ci_scope.plan(files, graph), len(graph.tests())),
        audit_line(audit_runs),
        "- measured on the graph of the tree at the week's end, not of each pull request",
        "",
        "## Size budgets (`quality/budgets.json`)",
        *budget_lines(budgets, ratchet.component_lines(), ratchet.core_components()),
        "",
        "## Component cards behind their code",
        *card_lines(_cards_behind(components)),
        "",
    ]


def gather(week: str) -> str:
    repo = _repo()
    start, end = week_bounds(week)
    _git("fetch", "-q", "origin", "main")
    pulls = _api(f"repos/{repo}/pulls?state=closed&per_page=100&sort=updated&direction=desc")
    merged = []
    for pull in pulls:
        if pull["merged_at"] and start <= parse_time(pull["merged_at"]) < end:
            detail = _api(f"repos/{repo}/pulls/{pull['number']}")
            merged.append(
                {**pull, "additions": detail["additions"], "deletions": detail["deletions"]}
            )
    window = f"{start:%Y-%m-%d}..{end:%Y-%m-%d}"
    fields = "{path,head_branch,event,conclusion,created_at,updated_at,run_attempt}"
    all_runs: list[dict[str, Any]] = []
    # Pages are fetched by number: `--paginate` follows links some proxies refuse.
    for page in range(1, 21):
        found = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/actions/runs?created={window}&per_page=100&page={page}",
                "--jq",
                f".workflow_runs[] | {fields}",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        all_runs += [json.loads(line) for line in found if line]
        if len(found) < 100:
            break
    ci_main = [
        r
        for r in all_runs
        if r["path"] == CI_WORKFLOW and r["head_branch"] == "main" and r["event"] == "push"
    ]
    reruns = sum(1 for r in all_runs if r["run_attempt"] > 1)
    trend = ratchet_trend(_baseline_at(start), _baseline_at(min(end, datetime.now(UTC))) or {})
    audits = [r for r in all_runs if r["path"] == AUDIT_WORKFLOW and r["event"] == "schedule"]
    scale = scale_sections(repo, merged, audits)
    return render(week, merged, red_time(ci_main, start, end), reruns, trend, ledger(), scale)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    today = datetime.now(UTC).isocalendar()
    parser.add_argument("--week", default=f"{today.year}-W{today.week:02d}")
    parser.add_argument("--write", action="store_true", help="write docs/metrics/<week>.md")
    parser.add_argument("--last", action="store_true", help="the ISO week before this one")
    args = parser.parse_args(argv)
    if args.last:
        prior = (datetime.now(UTC) - timedelta(days=7)).isocalendar()
        args.week = f"{prior.year}-W{prior.week:02d}"
    page = gather(args.week)
    if args.write:
        target = ROOT / "docs" / "metrics" / f"{args.week}.md"
        target.write_text(page, encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)}")
    else:
        print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
