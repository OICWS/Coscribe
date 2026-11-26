# A shared file preview and live Doc drafts (shipped)

Users can inspect generated Office files and see a Doc take shape without losing their place.

## Shipped

- Files uses the Doc viewer's read-only rendering for marked Markdown. It also renders PPTX slides,
  Word pages and Excel sheets. Files defers Office previews above the automatic size budget until
  the user chooses a viewer. Files beyond the Word or Excel file size limit can open externally.
- Generated Word and Excel cards open a read-only side panel when clicked. The original can open in
  Word or Excel for editing.
- Coscribe Docs can preview draft content from streamed file writes and text edits. In-progress
  content never writes to disk. The saved version reappears after cancellation or failure. The scroll
  container stays in place while content reflows and after the editor reloads the saved version.

## Not verified

- Native Windows Electron rendering and the Microsoft Office conversion engine on Windows.
