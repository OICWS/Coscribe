# Claude Code adds no signature to commits and pull requests (shipped)

Why: the repository forbids signature lines (the `signature-lines` check), but a cloud session's
pull request tool appended "Generated with Claude Code" to each description, so every new PR was
red until its body was edited.

## Shipped
- `.claude/settings.json` sets `attribution.commit` and `attribution.pr` to empty and
  `attribution.sessionUrl` to false, so Claude Code adds no `Co-Authored-By` trailer, no
  "Generated with" line and no claude.ai session link (the `Claude-Session` trailer and the link
  in a pull request description). A cloud session with one repository reads this file; it reads
  settings when it starts, so the next session shows the effect.

## Not verified
- Whether a session started after this is merged opens its pull requests without the line; if it
  does not, the footer comes from the GitHub tool, not from these settings.
