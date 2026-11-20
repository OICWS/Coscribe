# The "/" menu: a short list, new skills, and commands the app's controls already cover (shipped)

Why: issue #1003. Arrow keys moved the highlight past the menu's visible edge, so Enter could run
a command the person could not see; the menu fetched skills once, so a skill made later was
missing until a reload; long descriptions widened the menu or wrapped its rows; several entries
repeated a control; and a command typed during a reply reached the model as a note. The
maintainer chose what to keep in the issue's thread of decisions (2026-11-20).

## Shipped
- `frontend/src/components/CommandMenu.tsx`: the menu lists names only in a narrow column; the
  highlighted command's description shows beside it, whole, lifted to end where the list ends
  when it is long. The highlighted row
  scrolls into view on each arrow key, with wrap (`lib/useCommandMenu.ts`).
- The menu leaves out `/plan`, `/accept-edits`, `/stop` and `/saveworkflow`
  (`web/routes/settings/catalog.py`): the mode button and Stop do the same. Typed, they still run.
- During a reply "/" shows "Commands are available once this reply finishes." instead of the
  list, and a typed command stays in the box rather than reaching the model; `/stop` still stops.
- The mode button reads "Switching" from a pick until the server's state shows the new mode
  (during a reply the server applies it when the reply ends).
- `/clear` in the app archives the conversation and opens a blank one in the same environment
  (`useClearToNewChat`); no confirmation, since the archived one can be restored. The CLI's
  `/clear` still erases in place.
- `useSlashCommands` fetches `/api/commands` after every turn and when "/" opens the menu.
- `/saveskill` is now `/create-skill`, with no alias (the app has not been released).
- Descriptions corrected: `/init` refreshes an existing `OVERVIEW.md`.
- `tests/e2e/slash-menu.spec.ts` (nightly `e2e.yml`): scrolling, refresh, the description's
  place, `/clear` keeping the workspace, the held command during a reply, "Switching". The first
  two fail on `main`; the `/clear` one fails with the environment carry switched off.

## Not verified
- The menu in the Electron app on Windows; checked in Chromium on Linux only.

## Follow-ups
- `/doctor` is agreed and next; `/changes` waits on the maintainer (`docs/plan.md`).
