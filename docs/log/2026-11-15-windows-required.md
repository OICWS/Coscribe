# The Windows tests run on every pull request that changes code, so they can be a required check (shipped)

Why: the Windows job had its 14 green scheduled nights (decision 0009), but it ran on a pull
request only when a few listed files changed. A required check that never starts leaves a pull
request waiting for it forever, so it could not be made required as it was.

## Shipped
- `.github/workflows/windows.yml`: the `paths:` filter is gone; the job runs on every pull request
  to `main`, nightly and by hand. A pull request that changes documentation only (the rule of
  `scripts/ci_scope.py`, the same as the Linux `test` job's) runs none of its steps after the
  checkout and reports a pass, so a docs-only pull request does not wait for a Windows runner.
  The steps are skipped inside the job rather than the job skipped with `if:`, because a job
  skipped after a failed `needs:` also counts as passed.
- A pull request that changes code waits for the Windows run as well: about 12 minutes against
  the Linux job's 6, in parallel.
- `docs/plan.md`: the maintainer's step left is adding `pytest` to `main`'s required status
  checks; `docs/manual-checks.md` says when the job runs.

## Not verified
- The first runs on a pull request: the docs-only path is checked by this pull request's own
  run only for code (it changes a workflow and a script); a later docs-only pull request is the
  check that it reports a pass without running the tests.

## Follow-ups
- Once required, a Windows-only failure on a pull request blocks it; the flaky-test policy
  (`office-agent/CLAUDE.md`, one rerun, then an issue and a quarantine) applies there too.
