"""The flaky-test policy (tests/flaky_policy.py), run inside a throwaway pytest session."""

from __future__ import annotations

import datetime

import pytest

from . import flaky_policy

pytest_plugins = ["pytester"]

_CONFTEST = (
    "from tests.flaky_policy import *  # noqa\nfrom tests.flaky_policy import _quarantine  # noqa\n"
)


@pytest.fixture(autouse=True)
def _clean_state() -> None:
    flaky_policy._PASSED_AFTER_RERUN.clear()
    flaky_policy._RERUNNING.clear()


def _run(pytester: pytest.Pytester, body: str, *args: str) -> pytest.RunResult:
    pytester.makeini("[pytest]\nmarkers =\n    quarantine(issue, until): policy\n")
    pytester.makeconftest(_CONFTEST)
    pytester.makepyfile(body)
    return pytester.runpytest_inprocess(*args)


def test_a_quarantined_test_may_fail_until_its_date(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(flaky_policy, "_today", lambda: datetime.date(2026, 10, 15))

    result = _run(
        pytester,
        "import pytest\n"
        '@pytest.mark.quarantine(issue=7, until="2026-10-22")\n'
        "def test_flaky():\n    assert False\n",
    )

    result.assert_outcomes(xfailed=1)


def test_an_expired_quarantine_fails_the_test_and_names_the_issue(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(flaky_policy, "_today", lambda: datetime.date(2026, 10, 23))

    result = _run(
        pytester,
        "import pytest\n"
        '@pytest.mark.quarantine(issue=7, until="2026-10-22")\n'
        "def test_flaky():\n    assert True\n",
    )

    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*quarantine of this test ended on 2026-10-22*issue #7*"])


@pytest.mark.parametrize(
    "marker",
    ['quarantine(until="2026-10-22")', "quarantine(issue=7)", 'quarantine(issue=7, until="soon")'],
)
def test_a_quarantine_without_an_issue_or_a_real_date_stops_the_run(
    pytester: pytest.Pytester, marker: str
) -> None:
    result = _run(pytester, f"import pytest\n@pytest.mark.{marker}\ndef test_x():\n    pass\n")

    assert result.ret != 0
    assert "quarantine" in (result.stdout.str() + result.stderr.str())


def test_a_test_that_passes_on_the_rerun_is_reported_as_flaky(pytester: pytest.Pytester) -> None:
    result = _run(
        pytester,
        "import pathlib\n"
        "def test_flaky(tmp_path_factory):\n"
        "    marker = pathlib.Path(__file__).with_name('seen')\n"
        "    first = not marker.exists()\n"
        "    marker.write_text('x')\n"
        "    assert not first\n",
        "--reruns",
        "1",
    )

    assert result.parseoutcomes() == {"passed": 1, "rerun": 1}
    result.stdout.fnmatch_lines(["*flaky: failed, then passed on the rerun*", "*::test_flaky"])


def test_a_test_that_fails_on_the_rerun_too_is_a_failure_not_a_flake(
    pytester: pytest.Pytester,
) -> None:
    result = _run(pytester, "def test_broken():\n    assert False\n", "--reruns", "1")

    assert result.parseoutcomes() == {"failed": 1, "rerun": 1}
    assert "flaky: failed, then passed" not in result.stdout.str()
