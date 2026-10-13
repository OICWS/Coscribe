# Golden XML tests for pptx, part 2a: image decks; charts are not stable (shipped)

Why: Part 2 of the pptx goldens (issue #89) widens them toward about 20 decks before `tools/presentations.py` is split. This first group was meant to be charts and images.

## Shipped
- Stability probe: I built every deck twice, in separate processes (`PYTHONHASHSEED` 1 and 77, two seconds apart, different output folders), and compared every zip member.
- Four image decks are stable and now have goldens: a picture, a cropped picture whose image was then replaced, a picture with soft edge, shadow and glow, and a background image with a scrim. That makes 9 decks in `office-agent/tests/golden/pptx/`.
- Finding: chart decks (bar, line, pie) are not stable, so they are left out, as the issue asks. Exactly one member differs: `ppt/embeddings/Microsoft_Excel_Sheet1.xlsx`, the workbook python-pptx embeds with each chart (written by XlsxWriter 3.2.9 under python-pptx 1.0.2). Inside it, only `docProps/core.xml` differs: `dcterms:created` and `dcterms:modified` hold the time of the build, to the second, so the workbook differs on almost every run. Its other nine parts and its own zip member times (fixed at 1980) are identical. The chart XML itself is stable.
- `.gitattributes`: `office-agent/tests/golden/** -text`, so git never rewrites a golden's line endings.
- Each builder runs inside its deck's folder, so source images are written next to the deck. The five part-1 goldens are unchanged.

## Not verified
- On Windows: the nightly Windows job runs these tests.

## Follow-ups
- Charts, for the maintainer to decide. One option is for the canonicaliser to open embedded workbooks and blank the same two timestamps it already blanks in the deck's own `docProps/core.xml`. Another is to fix the time when a chart is built, which is a product change. Until then, chart code has no golden.
- Size: 9 goldens are about 1.1 MB. About 87% of each is the slide master, layouts and theme, identical in every deck except `theme` (which changes the master and the theme). A smaller form could keep those parts once, in a shared golden, with each deck's golden holding only the parts that differ. This is proposed here, not adopted.
