# A shared part's elements are edited from the panel (shipped, step 2)

Why: after step 1 (`docs/log/2026-11-03-design-shared-parts.md`), the panel showed a part's
elements but refused to edit them, so changing a tab's label meant asking coscribe.

## Shipped
- **Edits go into the part file.** An element inside a part is edited like any other: Properties
  fields, the Code tab, or a double click on its text. The change is written into `name.part.html`,
  so every artboard that places the part shows it.
  - The panel's note now says so.
  - The element that places the part (`coscribe-part`) has nothing to edit, so its fields stay
    disabled.
- **How it works** (`board_edits.board_edit_file`):
  - The edit finds which file the element lives in: the page, or the part when the path goes
    through a placed `coscribe-part`.
  - Inside a part, the element is counted from the part's own top-level elements (a `<style>`
    counts, as it does in the served page).
- **Undo is per canvas** (`board_undo.py`). Each step names the file it wrote (a page or a part).
  The panel's Undo and Redo work from any artboard: a part edited from one board is undone from
  another.
  - The steps stay only while every file the panel wrote is unchanged since. A file written by
    coscribe or anything else ends them, as before.
- **Next turn:** coscribe is told `tabs.part.html <b> …`, naming the part file.
- **Tests:**
  - `tests/test_board_edits.py`: where an edit goes; the placing element refused; a part edit
    undone from another page.
  - `design-canvas.spec.ts`: a double-click edit of a part's text shows on both boards, and only
    the part file changes. Then the page's heading is edited. Then both edits are undone from the
    other board. All 6 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
