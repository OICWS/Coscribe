# Parts several artboards share (shipped, step 1)

Why: a tab bar, header or cart bar that appears on every screen of a design had to be written into
each page, so a change to it meant rewriting them all, and the copies drifted apart.

## Shipped
- **A part** is `name.part.html` in the canvas folder. A page places it with
  `<coscribe-part name="name"></coscribe-part>`.
- **When it is served** (`design_canvas.with_parts`, called from `served_page`), the server fills
  the part into a `coscribe-part` element laid out with `display: contents`. Because the element
  stays, the page's other elements keep the places they have in the source, which the properties
  panel's edits count by.
  - The canvas, Play, the HTML/PDF export and `look_at_page` all show the filled page.
  - A missing part is drawn as a red dashed "Missing part: name" box.
  - A part does not place parts.
- **The Design skill** teaches parts:
  - when to use one;
  - the file and the tag;
  - prefixed classes;
  - styling the active tab from the page;
  - checking that every part a page places exists.
- **The properties panel:**
  - The element tree shows a part as `Part "name"` with its elements.
  - An element inside a part is shown with a note that it is in a shared part and that coscribe
    changes it. Its fields are disabled, and a double click does not edit it in place.
  - The server refuses such an edit as well (`board_edits._in_part`).
  - Elements of the page around the part are still edited as before.
- **Tests:**
  - `tests/test_design_canvas.py`: a part is filled in and a missing one is marked; a page of its
    own is not filled.
  - `tests/test_board_edits.py`: edits inside a part are refused; an element after the part is
    edited.
  - `design-canvas.spec.ts`: two boards show the same part. A double click in it only picks it,
    with the note. The page's heading after the part is edited in place. All 6 tests pass against
    a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- Not yet run with a real model: whether DeepSeek writes parts from the skill comes with the
  next Design evals.

## Follow-ups
- Edit a part's elements from the panel, writing into the part file (all artboards change).
