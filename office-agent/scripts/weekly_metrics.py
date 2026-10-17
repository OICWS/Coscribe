#!/usr/bin/env python3
"""The weekly metrics page (`docs/metrics/<week>.md`): how the week's changes went.

    python scripts/weekly_metrics.py                   # this ISO week so far, to stdout
    python scripts/weekly_metrics.py --week 2026-W42 --write

Lead time and size of merged pull requests, reverts, how long `main` was red, runs that needed a
second attempt, how the ratchet baseline moved and how many "Not verified" items the log holds.
It reads GitHub through `gh api` (REST) and the checkout through `git` (a shallow clone has no
baseline from the week's start, and the ratchet table then says n/a); it changes nothing but the
page it writes.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "docs" / "log"
LEDGER_FROM = "2026-10-08"
CI_WORKFLOW = ".github/workflows/office-agent-ci.yml"
BASELINE = "office-agent/quality/baseline.json"


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


def render(
    week: str,
    merged: list[dict[str, Any]],
    red: timedelta,
    reruns: int,
    trend: list[str],
    notes: dict[str, int],
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
    out += [f"- runs that needed a second attempt: {reruns}", "", "## Ratchet", ""]
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
    return render(week, merged, red_time(ci_main, start, end), reruns, trend, ledger())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    today = datetime.now(UTC).isocalendar()
    parser.add_argument("--week", default=f"{today.year}-W{today.week:02d}")
    parser.add_argument("--write", action="store_true", help="write docs/metrics/<week>.md")
    args = parser.parse_args(argv)
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
