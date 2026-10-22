# Docs: Export as Word, PDF and Markdown (shipped)

Why: the maintainer's reference (Claude Docs) offers a document as Word, PDF and Markdown from one menu.
The Word panel had none of them; a person had to find the file in the workspace.

## Shipped
- The document's title menu (in the viewer and in the editor) has **Export as Word**, **Export as PDF** and
  **Export as Markdown**, below the file's own entries.
- **Word** downloads the `.docx` itself. **Markdown** is written in the browser from the document's blocks
  (`lib/docsMarkdown.ts`): the title as `#`, headings one level down, bold, italic, links, lists nested by
  level, quotes, tables (GFM, with an empty header row when the file has none), dividers; a picture is
  the note `[Picture]` and a block the editor keeps as it is gives its text; page breaks and empty blocks
  are left out. **PDF** draws the document page by page in a hidden frame and opens the system's print
  dialog; "Save as PDF" there makes the file. A frame of its own keeps the app's page out of the print.
- A failed export says so in the panel's header.
- No server change: the Word download is the existing file download, the other two work from what the
  panel already reads.
- Tests: vitest for the Markdown writer; a Playwright spec that downloads the Word file and the Markdown
  file and reads the Markdown.

## Not verified
- The PDF path in a real browser and in the Electron app: headless Chromium opens no dialog (the spec
  checks the frame is drawn with the document's text, not the printed file). Electron's print dialog on
  Windows is the open question; if it does not offer "Save as PDF" the route is a server-side conversion.
- Pictures and charts are not in the Markdown; page layout is the viewer's, not Word's.

## Follow-ups
- The chat's end-of-turn file card and the inline file chip with a hover card (next, same reference).
