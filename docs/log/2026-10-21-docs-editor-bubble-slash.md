# Docs editor: a bar over selected words and a "/" menu (shipped)

Why: the first editor (see `2026-10-21-docs-editor-panel.md`) had only the toolbar. The maintainer's
reference (Claude Docs) edits with a bar that follows the selection and a "/" menu for inserting.

## Shipped
- Selecting words shows a bar over them: bold, italic, underline, link (the app's own dialog) and
  **Ask coscribe**, which sends a message quoting those words and the file (the same hand-off the page
  view has). The bar is not shown over a locked block.
- Typing "/" at the start of a block or after a space opens a menu: Heading 1–3, Bulleted list,
  Numbered list, Quote, Table. Typing narrows it by name or by what people call it ("grid" finds Table);
  arrows move, Enter or Tab picks, Escape closes. It does not open inside a table, whose cells hold one
  plain paragraph.
- New dependency `@tiptap/suggestion` (MIT, 3.32.0); the bubble comes from `@tiptap/react`, already there.
- Tests: the menu's matching (vitest) and a Playwright spec: "/" makes a heading and a table, a cell takes
  no menu, and bold from the bar is written to the file.

## Not verified
- The bar and the menu with a Chinese input method (an open composition and "/" or a selection);
  in the packaged app on Windows.
- The menu on a very small window, and with a screen reader.

## Follow-ups
- Images, a divider and a page break (they need the writer to take them), undo that covers coscribe's
  turns, and telling coscribe what the person edited: in `docs/plan.md`.
