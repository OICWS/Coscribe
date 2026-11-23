# Checks on what a pull request's tests prove: fails before, changed-line coverage, the review link (shipped)

Why: the 2026-10-11 assessment (§4) found that only a test that fails without a change shows
what the change does, and that changed-line coverage was a report nobody had to act on. Review
on invariant paths was a rule the PR template asked for and nothing checked. Part of #1051.

## Shipped
- `scripts/pr_gates.py fails-before` and the `PR tests` workflow: a pull request that changes
  code under `office-agent/src/` must change a test, and one of its changed test files must fail
  on the merge base's code (this pull request's tests run against the base's `src`, stopping at
  the first failure, or after 600 s, which counts as failing). It runs again when the
  description is edited. A `Fails before: <why>` line waives it.
- `scripts/pr_gates.py coverage` in the `test` job: the changed lines are at least 80% covered
  once 5 or more are measurable (diff-cover 10.6.0), the rule
  `docs/assessments/2026-10-13-diff-coverage.md` measured (2 of 17 pull requests would have
  failed, each for want of one test). A `Changed-line coverage: <why>` line waives it.
- `scripts/pr_gates.py review` in `PR text` (`independent-review`): a change to an invariant
  path (the list in `office-agent/CLAUDE.md`) must link a GitHub review that exists on the same
  pull request. No line waives it.
- Fails-before replayed on the last 15 commits on `main` that changed code (#1030 to #1048):
  in each, a changed test fails on the base's code, so the rule would have blocked none of them;
  on #1043 the run took 6 s, because it stops at the first failure.

## Not verified
- The three jobs on a real pull request until this one runs them; the invariant-path review was
  checked with a fake GitHub answer, not against the API.

## Follow-ups
- The maintainer makes `PR tests / fails-before` and `PR text / independent-review` required
  checks.
