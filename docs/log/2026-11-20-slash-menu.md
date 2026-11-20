# The "/" menu keeps its highlight in view and offers new skills (partly shipped)

Why: issue #1003. Arrow keys moved the highlight past the menu's visible edge, so Enter could run
a command the person could not see; the menu fetched skills once when the app loaded, so a skill
made later was missing until a reload; and some command descriptions no longer said what the
command does.

## Shipped
- `frontend/src/lib/useCommandMenu.ts`: the menu's matching and highlight, moved out of
  `Composer.tsx`; the highlighted row scrolls into view on each move (both arrow keys, with wrap).
- `useSlashCommands` fetches `/api/commands` after every turn and each time "/" opens the menu,
  so a skill made in chat, in Settings or on disk is offered without a reload.
- `web/routes/settings/catalog.py`: `/accept-edits` says that only file edits skip approval
  (`approvals.py` auto-approves `WRITE_LOCAL` alone), `/plan` uses the mode button's wording,
  `/init` says it refreshes an existing `OVERVIEW.md` (the prompt already did).
- `tests/e2e/slash-menu.spec.ts` (in the nightly `e2e.yml` list): both specs fail on `main` and
  pass with the change.

## Not verified
- The menu in the Electron app on Windows; checked in Chromium on Linux only.

## Follow-ups
- The rest of #1003 waits on the maintainer: which commands leave the menu, what a typed command
  does during a reply, the mode button's pending state, `/clear`, `/saveskill`'s name and the
  new commands from the issue's comment (`docs/plan.md`).
