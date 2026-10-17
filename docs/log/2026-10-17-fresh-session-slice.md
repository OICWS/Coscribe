# Fresh-session slice measured (shipped)

Why: #388 item 4. The slice budget (15 files, 150k tokens) had only a static estimate.

## Shipped
- `docs/metrics/2026-10-17-fresh-session-slice.md`: three fresh sessions each made a small change in
  `tools.office.docx`, `web` and the frontend; 5 to 9 files and 4.5k to 5.6k tokens read, all inside
  the budget.
- The docx card names where the tool wrapper and the implementation live; `office-agent/CLAUDE.md`
  explains running tests in a git worktree.

## Not verified
- Sub-agents stand in for sessions a person starts; the token counts are estimated from file sizes.

## Follow-ups
- A frontend card and the web card's error-body convention (docs/plan.md).
