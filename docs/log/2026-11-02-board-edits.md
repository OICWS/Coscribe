# The properties panel edits an artboard's element and writes it into the page (shipped)

Why: step 2 of the canvas's properties panel (`docs/plan.md`). After step 1 the person could see
an element's style, but changing it meant asking coscribe.

## Shipped
- **What can be edited.** On the Properties tab, an element's text, width and height, font size
  and weight, colour, background, corner radius, padding, gap and opacity are fields.
  - A field saves on Enter or when it loses focus. Escape puts the old value back.
  - After a save the board is served anew and the same element is picked again.
  - Layout and position stay read only.
- **How it is written** (`conversation/board_edits.py`):
  - The element is found in the page's source by the inspector's path. Only its `style`
    attribute or its text is rewritten; every other byte stays as coscribe wrote it, including
    `var(--…)` references.
  - A page without a `<body>` tag is counted as the browser counts it. The first element a head
    cannot hold opens the body.
  - The write is refused when the element's tag, or its text before an edit, no longer matches
    the source. The panel then says to pick the element again.
  - A value that could break out of the attribute (`;`, quotes, `<`, a comment) is refused.
- **Route:** `PUT /api/threads/{thread_id}/canvas/element`.
- **Next turn:** coscribe is told once which design and which pages were edited ("[The user
  edited the design … since your last turn: …]"), as for slides and Docs (`user_edits.py`). The
  Design skill says to read those pages and keep the changes.
- **Inspector:** it also sends an element's whole text as the source has it (`content`). The
  shown text is cut to 60 characters and follows `text-transform`, so it cannot be compared with
  the source.
- **Tests:**
  - `tests/test_board_edits.py`: style and text written in place, an implied body, a refused
    stale pick or value, the note told once.
  - The canvas route test in `tests/web/test_artifacts.py`.
  - `design-canvas.spec.ts` sets a font size and a text from the panel and reads both in the
    board and the file; all 4 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- A page the browser repairs in other ways (an unclosed `<p>`, a table without `<tbody>`) can
  count elements differently from the source. Such an edit is refused, not written in the wrong
  place.

## Follow-ups
- Undo for these edits.
- The Code tab editable.
