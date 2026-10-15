"""The flaky-test policy as pytest hooks, imported by conftest.py.

A test that fails and then passes on the one rerun CI allows (`--reruns 1`) is not green:
it is reported at the end of the run and in the job summary, and the next step is an issue
and `@pytest.mark.quarantine(issue=N, until="YYYY-MM-DD")`. A quarantined test still runs
and may fail without failing the run, but only until the date: after it, the test fails
with a message naming the issue, so a quarantine cannot sit there for good.
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path

import pytest

_PASSED_AFTER_RERUN: dict[str, int] = {}
_RERUNNING: set[str] = set()


def _today() -> datetime.date:
    return datetime.date.today()


def _quarantine_terms(marker: pytest.Mark, nodeid: str) -> tuple[int, datetime.date]:
    issue = marker.kwargs.get("issue")
    until = marker.kwargs.get("until")
    if isinstance(issue, bool) or not isinstance(issue, int) or not isinstance(until, str):
        raise pytest.UsageError(
            f'{nodeid}: write @pytest.mark.quarantine(issue=<number>, until="YYYY-MM-DD")'
        )
    try:
        return issue, datetime.date.fromisoformat(until)
    except ValueError:
        raise pytest.UsageError(f"{nodeid}: until={until!r} is not a YYYY-MM-DD date") from None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """A malformed quarantine stops the run at collection, not when the test is reached."""
    for item in items:
        marker = item.get_closest_marker("quarantine")
        if marker is not None:
            _quarantine_terms(marker, item.nodeid)


@pytest.fixture(autouse=True)
def _quarantine(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("quarantine")
    if marker is None:
        return
    issue, until = _quarantine_terms(marker, request.node.nodeid)
    if _today() > until:
        pytest.fail(
            f"The quarantine of this test ended on {until}: fix it or delete it "
            f"(issue #{issue}), do not extend the date without a reason on the issue.",
            pytrace=False,
        )
    request.applymarker(
        pytest.mark.xfail(reason=f"quarantined until {until}, issue #{issue}", strict=False)
    )


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """The controller sees every worker's reports, so this works under xdist."""
    if report.when != "call":
        return
    if report.outcome == "rerun":
        _RERUNNING.add(report.nodeid)
    elif report.outcome == "passed" and report.nodeid in _RERUNNING:
        _PASSED_AFTER_RERUN[report.nodeid] = _PASSED_AFTER_RERUN.get(report.nodeid, 0) + 1


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    # A xdist worker has its own copy of the state; only the controller reports.
    if not _PASSED_AFTER_RERUN or hasattr(terminalreporter.config, "workerinput"):
        return
    lines = [f"  {nodeid}" for nodeid in sorted(_PASSED_AFTER_RERUN)]
    terminalreporter.section("flaky: failed, then passed on the rerun", sep="=", yellow=True)
    terminalreporter.write_line("\n".join(lines))
    terminalreporter.write_line(
        "Open an issue for each and quarantine it: "
        '@pytest.mark.quarantine(issue=N, until="YYYY-MM-DD"), at most a week out.'
    )
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        body = [
            "## Flaky tests (failed, then passed on the rerun)",
            *(f"- `{n}`" for n in sorted(_PASSED_AFTER_RERUN)),
        ]
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(body) + "\n")
