# PowerPoint: a deck built from pages takes half the time (shipped)

Why: a deck took 6-8 builds and 10-14 minutes. Its final pages were clean when built again
offline (8 decks of tasks 13 and 14: one error and a few number warnings in all of them), so the
builds were not spent on findings the model could not fix. Timing each tool showed the loop:
- every `render_pptx_preview` also ran the old route's geometric checks, which report 44-45
  "overlaps" on a deck the build finds clean (a two-line title, a figure over its caption); the
  model fixed them, rebuilt and previewed again, 5-6 times a deck (294 s of task 14's 616 s);
- the coordinator and `review_work`'s own description ask for a reviewer round after any
  multi-slide deck, so each deck also got two, each sending every slide image to a vision model
  (47-110 s).

## Shipped
- `render_pptx_preview` on a deck built from pages returns the images only, while every slide is
  still as its build wrote it (a `build.json` next to the deck names it and the slide hashes
  match); a deck edited since gets the full checks. The preview's body moves from
  `presentations.py` to `office/pptx/qa.py` (the big file is 20 lines shorter).
- A `build_pptx_from_pages` result with no errors and no warnings says what is next: preview
  once, change only what is clearly wrong, no `review_work`. A first try put this in the
  coordinator's review rule; the prompt line alone did not stop the reviewer rounds in a run, the
  tool result did, so the system prompt stays as it was.
- The number check leaves out a power of ten in brackets, a unit label: "(10,000 units)" under a
  万辆 axis was flagged on three pages of task 14. A round number in the text is still checked.
- The evaluation records each deck build's errors and warnings by page (`builds` in
  `result.json`) and the seconds spent in each tool (`tool_seconds`), a deferred tool under its
  own name.

## Checked
Tasks 13 and 14 (DeepSeek, effort low), before (the theme run from `main`) and after:

| | builds | previews | reviews | minutes | yuan |
|---|---|---|---|---|---|
| 13 before | 6 | 5 | 2 | 12.7 | 0.83 |
| 13 after | 2 | 1 | 0 | 6.4 | 0.45 |
| 14 before | 6 | 5 | 2 | 10.8 | 0.59 |
| 14 after | 3 | 1 | 0 | 6.1 | 0.38 |

Facts 6/6 and 8/8 as before, no number left that the inputs do not have. The maintainer's review (on the PR) narrowed the preview and the hint to an
unchanged deck and a build with no findings; the measured runs predate that, with the same flow
for a clean deck. A run with only the
preview change had 3 builds and 2 previews on task 13 but still two reviewer rounds (110 s).

In the LibreOffice render of task 14 a few long titles wrapped onto their English subtitle; the
maintainer opened both decks in PowerPoint on Windows and nothing overlaps there, so it is
LibreOffice's fallback for Microsoft YaHei, not a defect a reviewer round would have caught.

## Not verified
- In the app on Windows: how long the maintainer waits for a deck.
