# How many recent PRs would fail an 80% changed-lines coverage rule: 2 of 17 (shipped)

Why: CI prints the coverage of the lines a pull request changes but does not enforce it. `docs/plan.md` step 8 waited for numbers before deciding whether to fail a PR below 80% (issue #94).

## Shipped
- `docs/assessments/2026-10-13-diff-coverage.md`: a table of the last 20 merged PRs that changed Python under `office-agent/src/` (#32 to #78), the method and its limits. No CI, script or code changed.
  - 17 had measurable lines.
  - 1 would fail at 70%, 2 at 80%, 6 at 90%.
  - The two 80% failures were small (2 and 11 lines) and needed one test each.
  - The extra 90% failures are pure moves of untested route code (#50, #52), a Windows-only branch that Linux CI cannot run (#59), and a WebSocket notification without a test (#32).
- Method: the suite was run with coverage at each PR's squash commit, then `diff-cover` against its parent, with today's coverage settings for every PR. For the three PRs whose CI run printed a figure (#72, #76, #78), the recomputed figure is identical.
- `docs/plan.md` step 8 carries the finding.

## Not verified
- The 17 recomputed figures ran on Python 3.13 and CI runs 3.11; the three cross-checks agree, the rest are not checked against CI.
- Coverage of Windows-only code: CI measures on Linux only.

## Follow-ups
- For the maintainer: whether to enforce, at what threshold, and whether to exempt changes under about 5 measurable lines and pure moves.
