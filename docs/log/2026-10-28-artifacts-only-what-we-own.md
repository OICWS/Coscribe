# The Artifacts page lists only what coscribe made from a source it owns (shipped, part 1)

Why: decision 0027. A Word or Excel file is a file for Word or Excel, and a deck the person brought
and coscribe changed is theirs.

## Shipped
- `ARTIFACT_KINDS` has no `.docx` and no `.xlsx`: they are not described, so not listed, whatever the
  registry still holds.
- A `.pptx` is adopted only when the conversation created it (`activity`'s action `created`);
  one read, edited in place or replaced whole by a script is not. A Doc or a design still counts when
  replaced whole.
- The Word excerpt code is gone: a Doc's excerpt is the only one.
- Tests moved to Docs, decks and designs; new ones: a Word and an Excel file are not described, a
  brought deck is not adopted however changed.

## Not verified
- The page in a browser, and old registry entries for `.docx` / `.xlsx` (they are skipped, not
  deleted).

## Follow-ups
- Part 2: remove the Word editor, its panel menu, and its routes' front end; stop opening a `.docx`
  chip in the app.
- Part 3: remove the `sheets` kind from the wire types, the Artifacts tool and the page.
