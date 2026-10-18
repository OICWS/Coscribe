# The ratchet is enforced, and a test keeps it wired (shipped)

Why: batch 10 item 3 (#425) said `--enforce` was still report-only.

## Shipped
- It was not: `scripts/check.sh` has run `ratchet.py --enforce` and the CI `test` job runs
  `check.sh`, so a worse number has failed the merge already. `docs/plan.md` still said "next,
  `--enforce` after a week"; it now says what is true.
- Checked by breaking a metric: on a clean tree `--enforce` exits 0; with a 122-line function added to
  `tools/files.py` it exits 1 and names `file_lines`, `long_functions` and `dead_code` as worse.
- `test_the_checks_every_pull_request_runs_enforce_the_ratchet` fails if `check.sh`, the CI job or
  the Windows job stops calling it (shown by removing `--enforce` from `check.sh`).
- The baseline is one entry tighter (`code_runtime/install.py` method `readable` is gone).

## Not verified
- CI runs `check.sh` only when its scope step says `full`; a pull request that changes only docs
  skips it, which is unchanged.
