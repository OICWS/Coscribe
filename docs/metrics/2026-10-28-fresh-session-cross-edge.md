# Fresh-session slice, changes that cross a component edge (2026-10-28)

What this is: #677 item C, same method as `2026-10-17-fresh-session-slice.md`. Four sub-agents with an
empty context, each in its own worktree, were given one change and the discovery protocol in the root
`AGENTS.md`, and told not to use `slice.py`. Each reported every file it opened. Lines read are the
agents' own counts; tokens are lines times 12 (about 48 characters a line, divided by four), a rough
figure. The changes were thrown away.

| Change | Components crossed | Files opened | Lines read | Tokens read (est.) | Session context (tokens) | Right first place? |
|---|---|---|---|---|---|---|
| A new Profile setting "Reply language" | `web`, `frontend` | 11 | ~760 | ~9k | ~73k | yes (by a repo-wide grep) |
| `edit_docx_review` takes `initials` | `tools.office.docx` (read path already existed through `web` and `frontend`) | 8 | ~710 | ~8.5k | ~79k | yes (by component name) |
| The state event carries `pending_steers`, the composer shows it | `conversation`, `frontend` (and a `web` test) | 7, plus 6 read in ranges | ~620 | ~7.5k | ~73k | yes |
| Web search takes `max_results` (a likely wrong turn: `tools/web` against the server package `web/`) | `tools.web` | 7 | ~450 | ~5.5k | ~64k | yes |

All four stayed far inside the budget (15 files, 150k tokens). Each ran its checks; three finished the change and
passed them (the Profile setting: 38 pytest, build and vitest; the state field: build, 380 vitest, wire check; web search: 12
pytest). The Word sample passed 93 pytest but could not regenerate `tests/tool_schemas.txt`.

## Findings
- **No wrong turn, even on the sample built to cause one.** The root layout table says "Built-in tools" for
  `tools/`, so "web search" went to `tools.web` and not to the server package `web`.
- **The cards found the component, not the files.** In the Profile sample the cards named neither the settings
  allowlist nor the Settings modal's `CONFIG_KEYS` list; a repo-wide grep for the existing fields found both. In the
  state-field sample the cards said how to regenerate the wire types but not the chain after it (reducer,
  `App.tsx`, composer) nor that `tests/web/test_chat_modes.py` holds the whole state payload: a failing test showed it.
- **The tool-schema snapshot cost two sessions.** Its test is skipped on Python 3.13, which is what the sandbox
  has, so the Word session changed a signature, could not regenerate `tests/tool_schemas.txt` and left it stale; the
  web-search session lost time finding out. Only a decorator in the test says why.
- **The docx card sent no one wrong, but stops at the tool.** It had no pointer to the read path of the Word panel,
  which the session found by grep (it was already complete there). The Word editor was removed afterwards (#693), so
  no card line was added for it.
- `docs/components.md` has no keywords, so a grep in it for `web_search` found nothing; sessions used it only to learn the
  component names.
- `gen_wire_ts.py --help` regenerates the file silently; only `--check` verifies.
- One sentence in the Profile brief was wrong: the profile values are not handed to the agent anywhere today
  (`config.py` says the browser only reads them). The session said so and stopped. That is the brief's fault.

## What changed (item D)
- `frontend/AGENTS.md`: the chain a new state field goes through, the settings chain (allowlist, type, `CONFIG_KEYS`)
  and that `gen_wire_ts.py` writes on every run.
- `conversation/AGENTS.md`, `web/AGENTS.md`: the state payload test and the settings allowlists.
- `office-agent/CLAUDE.md`: a signature change edits `tests/tool_schemas.txt`, the test is skipped on Python 3.13, how to
  regenerate it on 3.11.

## Not verified
- Sub-agents, not separate top-level sessions: they share this session's model and instruction files. Four changes, one
  run each, so the figures are not a distribution.
- Token counts are the agents' line counts times 12, not a billing count; the session context figures are the harness's
  totals for the whole run, tool output included.
- A change in `conversation/session.py` as such was not tried; the state-field change touches `send_state` in it, but
  as a one-line addition.
- The docx card's "being changed by #343" line was left as it is; the issue is still open.
