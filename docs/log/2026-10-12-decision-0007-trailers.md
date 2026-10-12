# Decision 0007 no longer says commits carry trailers (shipped)

Why: 0007 said a person's sessions commit "with the two trailers" and that coordination comments carry "the attribution footer". The repository has since decided the opposite: a commit message, PR title or description has no `Co-authored-by`, session link or "Generated with/by" line, and the `PR text` check fails a pull request that has one (issue #81).

## Shipped
- `docs/decisions/0007-working-with-more-than-one-human.md`: the footer and the trailers are gone, the commit rule now matches "Commit authorship" in `office-agent/CLAUDE.md`. The record is 39 lines (limit 40) and keeps its status.

## Not verified
- Nothing beyond the docs tests.

## Follow-ups
- None.
