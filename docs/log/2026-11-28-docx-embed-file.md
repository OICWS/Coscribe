# A file embedded in a Word document opens from its icon (shipped)

Why: a person asks to insert a deck, a workbook or a PDF into a Word document so that clicking it
opens the file. The Word tools could only add a picture, so OfficeVal dev task 059 scored 0 (#1126).

## Shipped
- `embed_docx_file` (`tools/office/docx/_embed.py`): the file's bytes go into the document as an
  OLE Package (`_ole.py`, a compound file written in Python, as Word's "insert object from file,
  display as icon" does). The icon is a vector EMF (`_icon.py`) with a page, a badge for the
  file's kind and the file's name as real text, at most three lines.
- `in_cell_beside="<label>"` puts the icon on the first blank line of the cell to the right of a
  form's label, centred, in the font of that column's nearest text. `after_text` and the end of
  the document work as they do for `add_docx_image`.
- The tool result tells the model to leave the icon as it is. Without that note, runs resized the
  icon, added a hint line, removed the blank lines or added a hyperlink to the file on disk, and
  each of these lost points.
- Word skill: when to use it and what not to add.
- OfficeVal 059 (dev): 0 before; 0.9, 0.9 and 0.8 over three runs on `deepseek-flash`
  ($0.02 a run). The missing 0.1 is the dataset's deck, which differs from the one the verifier
  checks the bytes against.

## Not verified
- Double-clicking the icon in the real Word on Windows. LibreOffice lays the document out
  (4 pages, icon in the cell) and a compound-file reader (olefile) reads the package back.
- WPS.

## Follow-ups
- The same object in a PowerPoint slide or an Excel sheet.
