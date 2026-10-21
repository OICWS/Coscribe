# Docs editor: pictures are shown in the text (shipped)

Why: a paragraph with a picture was a grey "Picture or drawing" line, so the person edited a document
they could not see. Showing the picture is the first step; putting one in comes next.

## Shipped
- A locked paragraph lists the pictures it embeds (up to four relationship ids, `block_images.py`); the
  editor draws them in place of the grey bar, at their own size up to the column width and 420 px high.
  The paragraph stays locked: a save sends only its id, so the file keeps it exactly as it was.
- `GET /api/threads/{id}/docs/image?path=&rid=` serves one picture of the document: only PNG, JPEG, GIF
  and WebP (vector and legacy formats stay a grey line), only an id of the form `rId<n>` that is a part
  of that document, with `nosniff`. The url carries the file's version, so an edited file is a new picture.
- Tests: the reader lists a picture and `read_doc_image` refuses an unknown id and a part that is not a
  picture; the route serves it and answers 404 to a bad id, a missing one and a path outside the folder;
  a vitest case for the urls; a Playwright spec with a real picture (shown, and an edit beside it saves).

## Not verified
- A picture in a table cell (the whole table is locked and shows as a grey line), a floating or cropped
  picture (drawn whole, uncropped), and a picture of 4 or more in one paragraph (the first four).
- The packaged app on Windows.

## Follow-ups
- Insert a picture from a file or by paste (the writer must take a new picture), divider, page break, and
  undo across coscribe's turns: in `docs/plan.md`.
