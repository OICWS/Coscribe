# Fresh-session slice: three sample changes, measured

What this is: #388 item 4. Three fresh sessions (sub-agents with an empty context, each in its own
worktree) were given one small change and the discovery protocol in the root `AGENTS.md`, and told not
to use `slice.py`. Each reported every file it opened. Tokens are characters divided by four of the
parts read (a partial read counts only its lines); a grep counts as a hit list, not a file. The
changes were thrown away; this measures reading, not shipping.

| Change | Starts in | Files read | Tokens read | Injected by the harness, not read | Budget (15 files, 150k) |
|---|---|---|---|---|---|
| `read_docx` gets `max_chars` | `tools.office.docx` | 9 | ~5.6k | `office-agent/CLAUDE.md`, `tools/AGENTS.md`: ~4.2k | inside |
| `DELETE /api/skills/{name}` answers 404 | `web` | 6 | ~4.7k | `office-agent/CLAUDE.md`: ~3.2k | inside |
| Effort picker gets an aria-label | `frontend` | 5 | ~4.5k | `office-agent/CLAUDE.md`: ~3.2k | inside |

Each session finished the change and ran its checks (docx 83 passed; web 25 passed; frontend build
and vitest passed). The sessions' whole context was about 70k tokens each, including the tool
output, far under 150k.

## Findings
- The static estimates in `2026-10-17-slice-budget.md` (27.8k for docx, 17.9k for the HTTP tool) were
  upper bounds: the sessions read 5 to 9 files and a fifth of that. Nothing was over budget, so `slice.py` and the
  protocol need no change.
- The frontend has no card: `docs/components.md` says "Card: none", so steps 3 and 4 of the protocol
  gave nothing and the session grepped (`effort`, 10 hits) and found the file at once. It also did
  not know the frontend unit-test pattern (vitest, `*.test.ts` beside the helper, node environment).
  This works for a small change; a larger UI change would be where it hurts.
- The docx card did not say which of `tools.py` (wrapper and docstring the model sees) and
  `toolkit.py` (implementation) to change, nor that a signature change touches
  `tests/tool_schemas.txt`. Fixed in the card.
- In a git worktree the venv imports the main checkout's `src` and `web/static/` is missing, so both
  the docx and web sessions first ran the wrong code or failed on the missing directory. Added to
  `office-agent/CLAUDE.md`.
- The web card does not say whether an error body uses `detail` or `error` (the skills routes use
  `error`).

## Not verified
- Sub-agents, not separate top-level sessions: they share this session's model and its instruction
  files, so a human-started session may read more. Token use is estimated from file sizes, not from
  a billing count.
- Only one change per area was tried.

## Follow-ups
- A frontend card (purpose, interface, unit-test pattern) and a note on the error-body convention in
  the web card; the frontend is left to the session working on it to avoid conflicts with the
  artifact work (docs/plan.md).
