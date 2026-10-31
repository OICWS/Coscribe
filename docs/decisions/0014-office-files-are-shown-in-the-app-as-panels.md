# 0014: Office files are shown in the app as panels; changes to them go through the backend

Status: accepted (2026-10-17, by the maintainer). Design: `docs/assessments/2026-10-17-file-viewers.md`.
Narrowed by 0025 (the Word panel is frozen) and 0027 (an Excel file is not an artifact; a Word
file is no longer edited in the app).

## Context
The model writes Word, PowerPoint and Excel files the user can only see by opening Office. Word
review (tracked changes, comments and replies) has no place in the app at all. The panel layout
(#334, #337, #338) now gives side panels a home beside the conversation. On 2026-10-16 an Excel
preview was dropped because a picture or a plain grid beside the chat was not worth its room;
the maintainer has since reviewed mockups of a Word review view, a slide viewer and a sheet grid,
each opened as a panel on demand.

## Decision
- One viewer panel shows a Word, PowerPoint or Excel file from the conversation. It is opened
  from a file card, Task details' Outputs or a tool row, and is moved, filled and closed like the
  other panels.
- **Word**:
  - pages are drawn in the app by docx-preview (Apache-2.0); the comment rail and the change
    controls are coscribe's own;
  - Review, Final (changes accepted) and Original (changes rejected) views.
- **PowerPoint**: the existing page previews, with a text outline when there are none.
- **Excel**: a grid drawn by the app from the file's values and formulas. This supersedes the
  2026-10-16 drop recorded in the Excel design, section 5.
- **Changes go through the backend.** Every change made in a viewer (accept or reject a change,
  reply, resolve, comment) is an operation on the real file. The same operations are model tools,
  `read_docx_review` and `edit_docx_review`. The viewer never edits a file itself.

## Consequences
- **Tool list**: two new deferred tools, so the tool schema snapshot changes in a reviewed PR
  (decision 0001).
- **Frontend dependency**: docx-preview (about 75 KB) and JSZip (about 98 KB), loaded only when
  a Word file is viewed.
- **Not Word's layout**: pages are not Word's exact layout (no automatic pagination, substituted
  fonts), so "Open in Word" stays one click away.
- **Experimental rendering**: docx-preview calls its change and comment rendering experimental.
  The viewer checks it against the backend's list and falls back to the rail without connectors.
- **Showing Office itself** inside the app stays out (2026-10-15).
