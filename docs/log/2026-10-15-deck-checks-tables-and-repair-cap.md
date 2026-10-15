# PowerPoint: the checker sees tables that grow, and repairs stop after two rounds (shipped)

Why: the judge of the side-by-side with ppt-master (`2026-10-15-deck-notes-and-ppt-master-side-by-side.md`)
found a table running into the footer that the checker missed. The maintainer also recalled early
builds whose checks sent the model round and round, each round costing money: a new check must
catch real defects only, and repairs must have an end.

## Shipped
- A native table's rows grow when a cell's text wraps, so it ends lower than its frame says. The
  checker estimates each row from its cells' text width against the column width, and reports an
  error only when the grown table runs into other text or off the page.
- The build records how many builds in a row had errors. From the third, the result says to stop
  repairing, deliver the deck and tell the user which pages still have problems; the guide already
  allowed two repair rounds, now the tool says so when they are spent.
- `tests/test_deck_engine_checks.py`: the table reaching the footer, the same table with columns
  wide enough (silent), and the stop after two repairs.

## Checked
- On every engine deck kept from earlier runs (146 decks, 704 pages), the table check reports one
  finding, the table the judge saw.
- A check for text running past its card was written and dropped: on those decks it raised 18
  findings, nearly all decoration the text is meant to cross (shapes running off the page, data
  bars with their labels outside), and it missed the one real case (a white card).
- The judge's other finding on coscribe's deck, a footer over a bullet, does not exist in the
  measured widths: LibreOffice in the evaluation has no Microsoft YaHei and draws a wider
  fallback font. Not a check.

## Not verified
- Row heights in PowerPoint itself: the estimate uses the emitter's text widths and PowerPoint's
  default cell margins.
