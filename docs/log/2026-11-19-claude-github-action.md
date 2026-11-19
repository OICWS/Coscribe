# @claude in issues and pull requests (shipped)

Why: the maintainer wants to ask Claude Code from GitHub itself (questions,
reviews, ideas, fixes) by mentioning `@claude`, billed to their Claude
subscription rather than to an API key.

## Shipped
- `.github/workflows/claude.yml` runs `anthropics/claude-code-action@v1` when
  `@claude` appears in an issue, an issue or PR comment, a review comment or a
  review. It signs in with the repository secret `CLAUDE_CODE_OAUTH_TOKEN`
  (made by `claude setup-token`). The action only answers people with write
  access, and Claude in it reads the root `AGENTS.md` through `CLAUDE.md`.

## Not verified
- A real run: it needs the Claude GitHub App on the repository and the secret,
  which only the maintainer can add.
