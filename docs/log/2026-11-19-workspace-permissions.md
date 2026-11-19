# A workspace's settings.json decides what asks (shipped)

Why: phase D of #926 (decision 0048). A workspace's `.coscribe/settings.json` holds
`permissions` as Claude Code's `.claude/settings.json` does: `deny`, `ask` and `allow` lists.

## Shipped
- Once the person accepted the folder, its rules decide the calls of that workspace's
  conversations that would otherwise wait for an approval. A rule is a tool name, a `*` pattern
  of names, or either with a pattern of its main argument: `run_background_command(git status*)`,
  `write_file(docs/*)`. Claude Code's tool names and `:*` syntax match nothing here. Deny wins
  over ask, ask over allow.
- A file never allows a call that leaves the machine (EXTERNAL) and a bare `*` allows nothing. A
  call holding two main arguments is never allowed by an argument pattern; deny and ask check
  each. A path is matched relative to the workspace with `..` folded (lower case on Windows), and
  a command with `;`, `&`, `|`, a backtick, `$(` or a newline isn't allowed by a prefix.
- They come after the person's own rules: a hook veto and exec policy's "forbidden" still win,
  plan mode still refuses, and a command that only the person may approve (decision 0022) still
  asks under an `allow`. An `ask` asks even where a standing approval or Auto mode would not.
- The file is read between two fingerprints, as `mcp.json` is, and the audit log records
  `workspace_settings` for what a rule decided; an `ask` card says the workspace asks.

## Not verified
- On Windows with a real model; the approval table runs the real decision with a fake socket.

## Follow-ups
- A rule decides only the calls that ask; a `deny` for a tool that never asks (reading a file)
  does nothing yet.
- `settings.json`'s `env`; the side panel's "Use them" card names the settings and their rules.
- The accepted settings are read for each gated call; they could be cached by the turn's
  fingerprint.
