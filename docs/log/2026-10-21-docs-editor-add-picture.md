# Docs editor: a picture is added from a file or by paste (shipped)

Why: pictures were shown in the text (`2026-10-21-docs-editor-pictures.md`) but could not be put in.

## Shipped
- Three ways in: the toolbar's Picture button and the "/" menu's Picture (both open the system file
  picker), and a picture pasted or dropped on its own (a screenshot, a file). Word's own pastes, which
  carry an image beside text, stay with the editor.
- The picture is a block that carries its data until the next save writes it into the file as a paragraph
  with an inline picture, no wider than six inches (a wider one is scaled down, height following). The
  save answers with the block's id and the data is dropped from the editor, so later saves send only the id.
- Refused with a plain line over the editor: anything but PNG, JPEG, GIF and WebP, and over 8 MB. The
  server checks the same (it reads the bytes, not the name or the type the browser said) and refuses a
  broken file.
- Tests: the writer (a picture added in the middle, a wide one scaled, a broken, non-picture, wrong-type
  and over-size one refused, the rest of the document untouched), vitest (data sent once, id only after),
  and a Playwright spec: Picture button, saved to the file, a text file refused with the line.

## Not verified
- Paste and drop of a real screenshot from the clipboard in a browser or the packaged app (the spec adds
  from the picker only); a picture added with the cursor in a table (refused with a line).
- Alt text and the picture's size are not editable yet.
- The packaged app on Windows.

## Follow-ups
- Divider, page break, picture size and alt text, undo across coscribe's turns: in `docs/plan.md`.
