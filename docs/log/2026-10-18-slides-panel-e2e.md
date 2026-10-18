# A Playwright spec for the Slides panel (shipped)

Why: batch 10 item 8 (#425). The Slides panel's editing, arranging and undo were only tested in
pieces (the engine in pytest, the source functions in jsdom); nothing drove the panel in a browser
against the real server.

## Shipped
- `frontend/tests/e2e/slides.spec.ts`, run nightly by `e2e.yml` (listed in `SPECS`). One test, in
  steps, each asserting on the server's files or `GET /api/threads/{id}/slides`, not only on the
  screen: slides and thumbnails; a comment (kept in `comments.json`); a click starts editing; a
  dragged element turns `01-cover.svg` into `01-cover.html` with the new `left`; a text box
  inserted and typed into; a slide from the New slide dialog; a slide duplicated, moved and
  deleted from the thumbnails; Undo and Redo from the zoom menu.
- The deck is built into the server's workspace by `tests/e2e/fixtures/build_deck.py` from the
  `COVER` and `CARDS` pages of `tests/test_deck_engine.py`. The spec skips itself when
  `COSCRIBE_E2E_WORKSPACE` is not set; `e2e.yml` sets it and installs `pytest`, which that test
  module imports.
- `scripts/stub_llm.py` calls a tool when the last user message has `[[stub-tool NAME {json}]]`
  (the reply after the tool result is still "OK"). The spec uses it for `read_pptx`, a read tool
  that runs without approval, so the deck appears under the thread's files and opens the panel.
- Product code is untouched (the Slides files are open to tests only).

## Checked by breaking
`save_slide` raising before it writes anything made the spec fail at the drag step (the page stayed
`01-cover.svg`); with the change reverted it passes (three runs in a row locally).

## Not verified
- Only Chromium on Linux against the local stack; the first run of the new spec on the CI runner
  is the pull request's own E2E run.
- Reading `/slides` while an arrange is renaming pages can return a 500 for a moment; the spec's
  polling tolerates it. Not changed here (product code); worth a look when step 5 of #425 is done.
