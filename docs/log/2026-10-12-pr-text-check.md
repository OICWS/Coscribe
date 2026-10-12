# A check that fails a PR carrying signature lines (shipped)

Why: a squash merge copies every commit message and trailer into the merged commit, so
`Co-authored-by`, session links and "Generated with Claude Code" lines made each merge longer
and had to be deleted by hand.

## Shipped
- `.github/workflows/pr-text.yml`: on every pull request it fails when the title, the
  description or a commit message has a `Co-authored-by` or `Claude-Session` line, a
  "Generated with/by Claude" line or a claude.ai session link. Not a required check.
- `office-agent/CLAUDE.md`: the rule, in the section on how a change reaches `main`.

## Not verified
- The pattern was tried on sample text with grep, not on a real pull request; this pull
  request's own run is the first.

## Follow-ups
- None. Make it a required check only if the maintainer wants merges blocked by it.
