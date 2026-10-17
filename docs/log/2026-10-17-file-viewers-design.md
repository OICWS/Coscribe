# File viewers designed: Word review, slides and sheets as panels (shipped)

Why: the maintainer reviewed mockups of a Word review view, a slide viewer and a sheet grid
(2026-10-16) and chose docx-preview to draw Word pages (2026-10-17).

## Shipped
- `docs/assessments/2026-10-17-file-viewers.md`: what the viewers are for, the viewer panel, Word
  (docx-preview pages with our own comment rail; every change made through backend operations
  that are also model tools), PowerPoint (existing previews, a text outline without them), Excel
  (a grid drawn by the app), the order of the PRs and the risks.
- Decision [0014](../decisions/0014-office-files-are-shown-in-the-app-as-panels.md); the Excel
  design's section 5 is marked superseded.
- Checked on the live run's redline: docx-preview 0.4.1 draws its two changes as `<ins>`/`<del>`
  elements and one marker per comment, and with changes off draws the accepted text.

## Not verified
- docx-preview on documents with tables, pictures, sections and long text: step 3 checks it.
