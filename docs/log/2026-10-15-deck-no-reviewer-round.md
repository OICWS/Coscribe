# PowerPoint: a deck built from pages gets no reviewer round (shipped)

Why: a deck took 6-8 builds and 10-14 minutes. Its final pages were clean when built again
offline (8 decks of tasks 13 and 14: one error and a few number warnings in all of them), so the
builds were not spent on findings the model could not fix. The tool counts showed the loop: 4-7
previews and 2 `review_work` rounds per deck. The coordinator asks for `review_work` with every
slide's image after any multi-slide deck, and the deck skill asks for one look; the model did
both, and each reviewer round sends every slide image to a vision model.

## Shipped
- The coordinator's review rule has one exception: not after `build_pptx_from_pages`, whose
  build checks every page and whose skill has its own one look. Other documents keep it.
- The evaluation records each deck build's errors and warnings by page (`builds` in
  `result.json`) and the seconds spent in each tool (`tool_seconds`), so the next question of
  where a task's time goes is answered from the run, not guessed.

## Checked
RESULTS

## Not verified
- In the app on Windows: how long the maintainer waits for a deck.
