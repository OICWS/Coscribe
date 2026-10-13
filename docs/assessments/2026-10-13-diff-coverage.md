# Changed-line coverage of the last 20 pull requests: would an 80% rule have failed them?

Author: kurtosisOC's session, 2026-10-13 (issue #94), on `origin/main` @ `2173dec`. Measured, not
estimated, except where a section says otherwise. No CI, script or code was changed.

## Answer

Of the last 20 merged pull requests that changed Python under `office-agent/src/`, **17 had
lines coverage can measure**. At 80%, **2 of 17 would have failed**; at 70%, 1; at 90%, 6. Both
80% failures were small. One was 1 of 2 lines (a log call), the other 3 of 11 (a fallback
branch), and one test each would have fixed them. The 90% failures add two pure moves of route
code, which a changed-line rule charges for code the PR did not write, and one Windows-only
branch, which CI on Linux can never run.

## Table

Covered percent is diff-cover's, statements and branches as `coverage.xml` reports them. "Lines"
counts the changed lines that coverage can measure, not the diff size.

| PR | Lines | Covered | 70% | 80% | 90% | What is not covered |
|---|---:|---:|---|---|---|---|
| #78 | 11 | 100% | pass | pass | pass | |
| #76 | 12 | 100% | pass | pass | pass | |
| #72 | 0 | n/a | n/a | n/a | n/a | comments and docstrings only |
| #66 | 2 | 50% | **fail** | **fail** | **fail** | a `logger.info` in the branch that skips a sub-agent report (`conversation/session.py`) |
| #63 | 207 | 95% | pass | pass | pass | error paths in `tools/conversations.py` and `conversation/session.py` |
| #62 | 12 | 100% | pass | pass | pass | |
| #61 | 10 | 100% | pass | pass | pass | |
| #60 | 3 | 100% | pass | pass | pass | |
| #59 | 27 | 88% | pass | pass | **fail** | the Windows `taskkill` branch and a `ProcessLookupError` race in `tools/background_tasks.py` |
| #55 | 108 | 98% | pass | pass | pass | 2 lines of `web/routes/ws.py` |
| #52 | 831 | 86% | pass | pass | **fail** | a pure move of routes out of `web/app.py`: the 112 lines were already untested |
| #50 | 613 | 89% | pass | pass | **fail** | the same, for the settings, files and skills routes (65 lines) |
| #51 | 23 | 100% | pass | pass | pass | |
| #48 | 0 | n/a | n/a | n/a | n/a | one changed line inside a dict literal, which coverage does not measure |
| #46 | 16 | 100% | pass | pass | pass | |
| #43 | 148 | 99% | pass | pass | pass | 1 line of `web/setup_app.py` |
| #41 | 35 | 100% | pass | pass | pass | |
| #37 | 0 | n/a | n/a | n/a | n/a | one string added to a set literal |
| #35 | 11 | 72% | pass | **fail** | **fail** | the conversation title taken from history when no first message is passed (`web/session.py`) |
| #32 | 103 | 86% | pass | pass | **fail** | the WebSocket push of background-task changes (`web/session.py`, 11 of 16 lines) |

Fails: 1 at 70%, 2 at 80%, 6 at 90%, of 17 measurable.

## What a rule would have cost

- **At 80%:** two tests.
  - #66: a test that a sub-agent's report is skipped and logged, a few lines.
  - #35: a test that a conversation without a first message takes its title from history.
  - Both PRs were under 15 measurable lines, so one uncovered line moves them by 9 to 50 points. A rule that ignores changes under about 5 measurable lines would not have failed #66.
- **At 90%:** also the four above 80%.
  - #52 and #50 moved untested code without changing it. A changed-line rule would have made a refactor pay for old gaps, or given it an exemption; those are the PRs the structure period wants more of.
  - #59's gap is a Windows-only branch. Windows is the only platform coscribe verifies (#88), but coverage runs on Linux, so such a branch counts as uncovered whatever tests exist.
  - #32 would have needed a test of the WebSocket notification.

## Method (repeatable)

1. PRs: `git log origin/main --format=%h -- 'office-agent/src/**/*.py'`, the newest 20. These are #32 to #78, merged 2026-10-09 to 2026-10-12. Only 23 such PRs exist so far.
2. For #72, #76 and #78, CI printed the figure: the "Coverage of the changed lines" step in the `test` job log of the PR's last run.
3. For all 20, I recomputed it at the PR's squash commit `<sha>`, in a git worktree:
   ```bash
   PYTHONPATH=<worktree>/office-agent/src python -m pytest -q -p no:cacheprovider \
     --cov=coscribe --cov-branch --cov-config=<rc> --cov-report=xml:cov.xml
   diff-cover cov.xml --compare-branch=<sha>^ --format json:dc.json
   ```
   `<rc>` is today's `[tool.coverage.run]` and `[tool.coverage.report]` from `office-agent/pyproject.toml`: source `coscribe`, branches on, the vendored files omitted. Commits before #68 had no coverage settings, so every PR is measured by the same rules. The built frontend was copied into each worktree.
4. Check: the recomputed figure equals CI's for all three PRs CI measured. That is #78 (11 lines, 100%), #76 (12 lines, 100%) and #72 (no measurable lines), with the same files listed.

## What could not be measured

- Python: the recompute ran on Python 3.13, CI on 3.11. The three PRs that CI measured agree exactly. For the others the figures may differ slightly where code is version-dependent.
- At three of the older commits, one test failed locally (`test_tool_schema_snapshot.py`, which compares against a snapshot taken on CI's Python). A failed test still records coverage for what it ran. The figures could be off only by what that one test alone covers.
- Windows: coverage is measured on Linux only. How much of the Windows-only code is covered is not known (the nightly Windows job does not measure coverage).
- Sample size: 20 PRs over 4 days (23 such PRs exist in all). A few small PRs swing the 80% count, so treat it as an order of magnitude, not a rate.
