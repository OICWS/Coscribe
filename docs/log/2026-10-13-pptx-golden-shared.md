# The pptx goldens keep the master, layouts and theme once (shipped)

Why: In #91, 9 goldens came to about 1.1 MB, and about 87% of each was the slide master, layouts and theme from python-pptx's template, the same in every deck except `theme`. At 20 decks that would be about 2.5 MB of repeated text. The review on #91 asked for this form before more decks are added (issue #89).

## Shipped
- `office-agent/tests/golden/pptx/_shared.txt` holds the canonical text of `ppt/slideMasters/`, `ppt/slideLayouts/` and `ppt/theme/` from the plain `bullets` deck. In a deck's golden, a part that is identical to its shared copy is written as `<same as _shared.txt>`; a part that differs is written out in full. The `theme` deck still shows its own master and theme, so theme code stays covered.
- A test checks `_shared.txt` against a fresh `bullets` build. Another checks that it parses back to the same text.
- Size: the 10 golden files are now 308 KB, down from about 1.1 MB.
- Pure move: for all 9 decks, rebuilding the full text from the new goldens and `_shared.txt` gives exactly the goldens on `main` before this change. Changing one character in `_shared.txt` fails 10 of the 12 tests: the shared test and every deck that refers to that part.

## Not verified
- On Windows: the nightly Windows job runs these tests.

## Follow-ups
- Part 2b: chart decks, with the canonicaliser blanking the two build timestamps in an embedded workbook's `docProps/core.xml` (the approach the review on #91 chose).
- More decks: icons, stat slides and the other layout directives, then templates, then audio and CJK text.
