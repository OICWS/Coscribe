# Only Windows is developed and verified (shipped)

Why: Nothing said which platform is supported, so sessions listed macOS (and sometimes Linux) under "Not verified" or spent effort on it (issue #88, from the review of #87).

## Shipped
- `AGENTS.md`: a two-line rule under the opening paragraph that every session reads. coscribe is developed and verified on Windows only. Linux is just where CI and cloud sessions run. macOS is not developed and is not listed as "not verified".
- `.github/PULL_REQUEST_TEMPLATE.md`: the "Not verified" hint names "a real Windows machine" instead of "a platform".
- `docs/start-guide.md` and `docs/plan.md` already agree with the rule; unchanged.

## Not verified
- Nothing beyond the docs tests. The macOS branches in the source (for example in `cli.py`) are untouched, as the issue says.

## Follow-ups
- None.
