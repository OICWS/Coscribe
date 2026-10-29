# A Word file opens in the editor only; the contents list lines up there (shipped)

Why: the maintainer found the Word panel's preview (Original / Review / Final) unneeded, and a
contents list lined up in the preview but not after Edit. "Make the editing mode good; there is no
need to fix the rendering."

## Shipped
- A Word file opens in the editor and there is no preview: `ViewerPanel.tsx` always shows
  `DocsEditorPanel`, which lost its "Word layout" button; `DocxPanelHeader` lost its Edit button.
- Removed with it, because only the preview used them: `DocxViewerPanel`, `DocxChangeBar`,
  `DocxCommentCard`, `DocxNewComment`, `docxActions`, the review calls in `lib/docxReview.ts`
  (what is left is `getDocxBytes`, which the exports use, and `isDocx`), `drawCharts` and
  `withoutStaleStyles` in `lib/docxChart.ts`, `docxReview.test.ts`, and the Playwright spec
  `docx-review` (also taken out of the nightly's list in `e2e.yml`). `docs-editor.spec` no longer
  clicks Edit or looks at the Word layout. The ratchet's baseline moved by the deleted
  100-line function and one unused export.
- The server's `docx-review` routes and the model's `read_docx_review` / `edit_docx_review` tools
  are untouched.
- In the editor, the first and last entry of a contents list (the paragraphs that hold the field's
  begin and end marks) are drawn as a locked line, and that line had `padding: 0 10px`, which the
  plain paragraphs do not, so those two sat 10 px further right (`index.css`). Measured in
  Chromium with the stylesheet's own rules, the three kinds of line start at x = 44.7 / 34.7 /
  44.7 before and 34.7 / 34.7 / 34.7 after.

## What the person can no longer do in the app
- Accept or reject a tracked change, and read, reply to, resolve or add a comment thread. The editor
  has none of these; they are in the removed preview. Tracked changes and comments in the file are
  kept as they are by the editor's saves, and Word shows them.

## Not verified
- The editor on a real contents list in the running app: the alignment was measured on a page with
  the stylesheet's rules and the same markup.
- The `docs-editor` spec was edited, not run (it needs a live server and the stub model).

## Follow-ups
- If the review actions are wanted back, they belong in the editor, not in a second view. The
  removed code is in this PR's history.
