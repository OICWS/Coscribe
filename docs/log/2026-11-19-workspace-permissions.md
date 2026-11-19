# A workspace's settings.json decides what asks (shipped)

Why: phase D of #926 (decision 0048). A workspace's `.coscribe/settings.json` holds
`permissions` as Claude Code's `.claude/settings.json` does: `deny`, `ask` and `allow` lists.

## Shipped
- Once the person accepted the folder, its rules decide the calls of that workspace's
  conversations that would otherwise wait for an approval. A rule is a tool name, a `*` pattern
  of names, or either with a pattern of its main argument: `run_command(git status*)`. Deny wins
  over ask, ask over allow.
- They come after the person's own rules: a hook veto and exec policy's "forbidden" still win,
  plan mode still refuses, and a command that only the person may approve (decision 0022) still
  asks under an `allow`. An `ask` asks even where a standing approval or Auto mode would not.
- The file is read between two fingerprints, as `mcp.json` is, and the audit log records
  `workspace_settings` for what a rule decided.

## Not verified
- On Windows with a real model; the approval table runs the real decision with a fake socket.

## Follow-ups
- A rule decides only the calls that ask; a `deny` for a tool that never asks (reading a file)
  does nothing yet.
- `settings.json`'s `env`; the side panel's "Use them" card names the settings.
