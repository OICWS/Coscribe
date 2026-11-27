"""Checks on what a pull request's tests prove (assessment 2026-10-11 §4, #1051).

    python scripts/pr_gates.py coverage diff-coverage.json
        The lines the pull request changed are at least 80% covered, when it changed at least
        5 lines coverage can measure (`docs/assessments/2026-10-13-diff-coverage.md`).
    python scripts/pr_gates.py fails-before --base <sha>
        A pull request that changes coscribe's code changes a test, and at least one of its
        changed test files fails on the base's code: a test that passes without the change
        does not show what the change does.
    python scripts/pr_gates.py review --base <sha> --head <sha> --pr <n>
        A pull request that changes an invariant path links an independent GitHub review posted
        on it (office-agent/CLAUDE.md, "Code review").

The description (`PR_BODY`) can say why a rule does not apply, on a line of its own:
`Changed-line coverage: <why>` or `Fails before: <why>` (a pure move, a Windows-only branch,
a change no test can observe). The review has no such line. CI reads the description when the
job starts: after editing it, run the job again.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # office-agent/
REPO = ROOT.parent

FAILS_BEFORE_TIMEOUT = 600
COVERAGE_FLOOR = 80.0
COVERAGE_MIN_LINES = 5

# office-agent/CLAUDE.md, "Code review": the paths whose change needs an independent review.
INVARIANT_PATHS = (
    re.compile(r"office-agent/src/coscribe/runtime/secrets[^/]*\.py"),
    re.compile(r"office-agent/src/coscribe/runtime/secret_store\.py"),
    re.compile(r"office-agent/src/coscribe/runtime_lg/tool_deferral\.py"),
    re.compile(r"office-agent/src/coscribe/runtime_lg/mcp_oauth\.py"),
    re.compile(r"office-agent/src/coscribe/code_runtime/permissions\.py"),
    re.compile(r"office-agent/src/coscribe/coordinator\.py"),
)
SOURCE = re.compile(r"office-agent/src/coscribe/.+\.py")
TEST = re.compile(r"office-agent/tests/(?:.+/)?test_[^/]+\.py")


def exemption(label: str, body: str | None = None) -> str | None:
    body = os.environ.get("PR_BODY", "") if body is None else body
    match = re.search(rf"^\s*{re.escape(label)}:\s*(\S.*)$", body, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else None


def changed(base: str, head: str = "HEAD") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...{head}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def coverage(report: dict[str, object]) -> tuple[bool, str]:
    lines = int(str(report.get("total_num_lines") or 0))
    percent = float(str(report.get("total_percent_covered") or 0))
    if lines < COVERAGE_MIN_LINES:
        return True, f"{lines} changed lines coverage can measure: under {COVERAGE_MIN_LINES}."
    if percent >= COVERAGE_FLOOR:
        return True, f"Changed lines {percent:.0f}% covered ({lines} lines)."
    return False, (
        f"Changed lines {percent:.0f}% covered ({lines} lines), under {COVERAGE_FLOOR:.0f}%. "
        "Add tests for them, or say why not on a `Changed-line coverage:` line."
    )


def failures(junit: Path) -> int:
    return sum(
        1
        for case in ET.parse(junit).getroot().iter("testcase")
        if case.find("failure") is not None or case.find("error") is not None
    )


def fails_before(base: str, files: list[str]) -> tuple[bool, str]:
    if not any(SOURCE.fullmatch(f) for f in files):
        return True, "No code under office-agent/src changed."
    tests = [f for f in files if TEST.fullmatch(f)]
    if not tests:
        return False, (
            "The code changed and no test file did. Add a test that fails without the change, "
            "or say why none can on a `Fails before:` line."
        )
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "base"
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(tree), base],
            cwd=REPO,
            check=True,
            capture_output=True,
        )
        try:
            # The base's code with this pull request's tests: what the tests say without the change.
            shutil.rmtree(tree / "office-agent" / "tests")
            shutil.copytree(ROOT / "tests", tree / "office-agent" / "tests")
            (tree / "office-agent" / "src" / "coscribe" / "web" / "static").mkdir(exist_ok=True)
            junit = Path(tmp) / "junit.xml"
            env = {**os.environ, "PYTHONPATH": str(tree / "office-agent" / "src")}
            command = [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-n",
                "4",
                # One failure answers the question.
                "--maxfail=1",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit}",
                *[t.removeprefix("office-agent/") for t in tests],
            ]
            process = subprocess.Popen(
                command, cwd=tree / "office-agent", env=env, start_new_session=True
            )
            try:
                process.wait(timeout=FAILS_BEFORE_TIMEOUT)
            except subprocess.TimeoutExpired:
                # A test that hangs on the base's code and finishes on the change's is a test
                # the change makes pass: the fix of a hang looks like this.
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return True, (
                    f"The changed test files did not finish in {FAILS_BEFORE_TIMEOUT} s on the "
                    "base's code."
                )
            failed = failures(junit) if junit.is_file() else 0
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(tree)],
                cwd=REPO,
                check=False,
                capture_output=True,
            )
    if failed:
        return True, "A changed test fails on the base's code (the run stops at the first)."
    return False, (
        f"Every test in {', '.join(tests)} passes on the base's code, so none shows what the "
        "change does. Add one that fails without it, or say why none can on a "
        "`Fails before:` line."
    )


REVIEW_LINK = re.compile(r"github\.com/OICWS/coscribe/pull/(\d+)#pullrequestreview-(\d+)", re.I)


def review(files: list[str], body: str, pr: int, exists: Callable[[int], bool]) -> tuple[bool, str]:
    touched = sorted({f for f in files if any(p.fullmatch(f) for p in INVARIANT_PATHS)})
    if not touched:
        return True, "No invariant path changed."
    for number, review_id in REVIEW_LINK.findall(body):
        if int(number) == pr and exists(int(review_id)):
            return True, f"Invariant paths changed ({', '.join(touched)}); review {review_id}."
    return False, (
        f"Invariant paths changed ({', '.join(touched)}). Link the independent GitHub review "
        f"posted on this pull request under `## Independent review` "
        f"(https://github.com/OICWS/coscribe/pull/{pr}#pullrequestreview-<id>)."
    )


def _review_exists(pr: int) -> Callable[[int], bool]:
    def check(review_id: int) -> bool:
        repo = os.environ.get("GITHUB_REPOSITORY", "OICWS/coscribe")
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/pulls/{pr}/reviews/{review_id}",
            headers={
                "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return bool(json.load(response).get("id") == review_id)
        except OSError:
            return False

    return check


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="gate", required=True)
    cov = sub.add_parser("coverage")
    cov.add_argument("report", type=Path)
    fb = sub.add_parser("fails-before")
    fb.add_argument("--base", required=True)
    rv = sub.add_parser("review")
    rv.add_argument("--base", required=True)
    rv.add_argument("--head", required=True)
    rv.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)

    if args.gate == "coverage":
        ok, message = coverage(json.loads(args.report.read_text(encoding="utf-8")))
        label = "Changed-line coverage"
    elif args.gate == "fails-before":
        ok, message = fails_before(args.base, changed(args.base))
        label = "Fails before"
    else:
        body = os.environ.get("PR_BODY", "")
        ok, message = review(changed(args.base, args.head), body, args.pr, _review_exists(args.pr))
        label = ""
    print(message)
    if ok:
        return 0
    reason = exemption(label) if label else None
    if reason:
        print(f"Not applied: the description says why ({label}: {reason}).")
        return 0
    print(f"::error::{message}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
