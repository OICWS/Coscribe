# Every PDFium user holds the one lock (shipped)

Why: the Slides panel drew a deck coscribe did not build as blank thumbnails. For such a deck each
slide is a page of the deck's PDF, drawn by PDFium, and the panel asks for every thumbnail at once.
PDFium is not thread-safe, and `foreign_slide_svg` took no lock: twelve threads drawing pages of one
PDF took the Python process down with a segmentation fault (exit code 139), which on a user's
machine ends the server and any conversation it was running.

## Shipped
- `tools/_pdfium.py`: the one `PDFIUM_LOCK` (re-entrant). `office/pdf/text.py` and
  `tools/pdf_pages.py` already used a lock of their own for text and page images; they now share
  this one, so a text read and a page draw cannot overlap either.
- `view_foreign.foreign_slide_svg`, `_thumbnail.measure_page_words` and
  `_thumbnail._render_pdf_pages` hold it while a PDFium document is open.
- `tests/test_pdfium_lock.py`: a fake PDFium document that fails when used without the lock, for
  a foreign slide and for the preview page renders.

## Not verified
- That this is what the maintainer's blank thumbnails were: it is a reproduced crash with the same
  trigger (all thumbnails requested together), but it was not seen on that machine, with
  PowerPoint or WPS, or on Windows.
- A deck whose PDF export itself fails still shows the "not built by coscribe" notice, as before.

## Follow-ups
- A slide that cannot be drawn shows the browser's broken-image icon; a placeholder that says why
  would be better.
