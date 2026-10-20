# Claude Code adds no signature to commits and pull requests (shipped)

Why: the repository forbids signature lines (the `signature-lines` check), but a cloud session's
pull request tool appended "Generated with Claude Code" to each description, so every new PR was
red until its body was edited.

## Shipped
- `.claude/settings.json` sets `attribution.commit` and `attribution.pr` to empty, so Claude Code
  does not add a `Co-Authored-By` trailer or a "Generated with" line.

## Not verified
- Whether a cloud session's pull request tool honours the setting; the next PR a session opens
  shows it. If the line still appears, the footer comes from the GitHub tool, not this setting.
