# The Word editor is removed; a Word file is a file for Word (shipped, part 2 of decision 0027)

Why: decision 0027. The editor over a Word file's XML was the largest source of fidelity bugs, and
the people who use coscribe have Word.

## Shipped
- Frontend: the Word editor and everything only it used are gone: `components/docs/` (panel, toolbar,
  bubble, sheet, picture bar, slash menu, save hook), `DocxPanelHeader`, and `lib/docs*` (blocks to
  the editor's document, its extensions, locked blocks, look, merge, caret, slash, pictures, export)
  with their tests, the `docs-editor` Playwright spec and its name in the nightly list. A Word file
  is not "viewable" any more; a message can still mention one.
- Three pieces the Doc (Markdown) editor used moved to `components/doc/`: `LinkDialog`, `ImageIcon`,
  and `askAboutWords` (now in `lib/docComments.ts`).
- Server: `web/routes/docs.py`, the Word `docx-review` routes in `routes/threads.py` and their
  request models, `tools/office/docx/{blocks,block_images,block_breaks,block_tables,look,history,
  user_edits}.py`, `DocxToolkit.docx_original`, and the Word half of the note that tells coscribe
  what the person changed (`conversation/docs_edits.py` keeps the Doc half). The model's own
  `read_docx_review` / `edit_docx_review` tools, `write_docx` and `docx_from_markdown` stay.
- The `tools` interface lost ten names; the route snapshot and the OpenAPI snapshot lost the
  seven routes; the audited GET list lost four.
- The ratchet's baseline moved by the deleted code (the `DocxViewerPanel` function, an unused export).

## Not verified
- The app: what a click on a `.docx` file in the conversation does now (it should open in Word as
  any file the app does not show).
- The `docs-editor` and `docx-review` specs were deleted, not run.
- The npm packages only the Word editor used (`docx-preview`, perhaps `jszip`) are still in
  `package.json`.

## Follow-ups
- Part 3: the `sheets` kind in the wire types, the Artifacts tool's `kind` and the page.
- Remove the npm packages nothing imports.

The "Reviewer name" setting (`COSCRIBE_REVIEWER_NAME`, `Settings.reviewer_name`) and `rejected_copy` went with it: only the Word review panel used them.
