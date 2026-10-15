# A flaky test is reported, then quarantined with an end date (shipped)

Why: #232 item 7, guardrail 11 of the assessment (flaky-test policy).

## Shipped
- `tests/flaky_policy.py`, loaded from `tests/conftest.py`:
  - the run lists every test that failed and then passed on the rerun, at the end and in the job summary (`GITHUB_STEP_SUMMARY`);
  - `@pytest.mark.quarantine(issue=N, until="YYYY-MM-DD")`: the test still runs and a failure does not fail the run (an `xfail`); after the date it errors with the issue's number; a marker without an issue or with a bad date stops the run at collection.
- `scripts/check.sh` runs pytest with `--reruns 1` (`pytest-rerunfailures`, a dev dependency), so CI does too.
- `office-agent/CLAUDE.md` says what to do with a flake.
- Proved by breaking: a planted test that fails once and then passes is listed under xdist (`-n 2`) and in the summary file; a planted quarantine dated in the past errors with its message; a future one is an xfail. `tests/test_flaky_policy.py` covers each in a throwaway pytest session.

## Not verified
- The first real flake in CI; the ban on wall-clock assertions is a sentence in `CLAUDE.md`, not a check.

## Follow-ups
- A check for `elapsed <` style assertions, if the sentence is not enough.
