# `scripts/weekly_metrics.py` and the first weekly page (shipped)

Why: #348 item 8. How the week went (lead time, reverts, red `main`, the ratchet) was not written down anywhere.

## Shipped
- `office-agent/scripts/weekly_metrics.py [--week 2026-W42] [--write]` builds `docs/metrics/<week>.md`:
  merged PRs with the median and longest lead time and the size, reverts, hours `main` was red
  (a failed run of the CI workflow to the next green one), runs that needed a second attempt, the
  number of names in each ratchet metric at the week's start and end, and the "Not verified"
  ledger count. It uses `gh api` page by page, because `--paginate` follows links this
  environment's proxy refuses.
- `docs/metrics/2026-W42.md` is the first page (85 merged PRs, median lead time 0.3 h, `main` red for
  1.7 h, no reverts).
- `tests/test_weekly_metrics.py` covers the week bounds, the red-time rule, the ledger count and the
  ratchet table.

## Not verified
- "Runs that needed a second attempt" counts GitHub's `run_attempt` above 1 for every workflow, not
  only the test job, so it can differ from the flaky-test list in the CI summary.
- Nothing runs the script on a schedule yet; a clone with a shallow history shows `n/a` for the
  ratchet at the week's start.

## Follow-ups
- A scheduled run (a workflow cannot push to `main`; it would have to open a PR).
- The `needs-real-machine` issues: the log holds 219 entries with a "Not verified" item, so one
  issue each needs the maintainer's say first.
