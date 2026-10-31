# look_at_page: coscribe sees a Design or Dashboard page as the app draws it (shipped)

Why: step 6 of `docs/assessments/2026-10-29-design-and-dashboard.md` (#721, #739). The first Design
eval found faults only a look shows (a poster's last block running into its footer); coscribe could
write a page but never see it.

## Shipped
- `look_at_page(path, board?, scheme?)`, deferred and read only (`conversation/page_tools.py`): a
  canvas's artboards (four a call, or the one named) at their board size, or an `.html` page at
  1280 wide and as tall as it is (to 4,000 px), served exactly as the design route serves it
  (`served_page`, now shared: a dashboard's data, a canvas's variables, light or dark). It returns
  a report per page and each screenshot, downscaled to 1,568 px at most.
- The report (`conversation/page_shot.py`): script errors, loads the page tried (the page policy is
  a meta tag, so it has no network), a page wider than its board, text over text (glyph runs of
  different text sharing over a third of the smaller) and, on a fixed board, text past its edge.
- Drawn in the computer's own Edge or Chrome, headless, with a throwaway profile, started by the
  server as the user: Edge ships with every Windows, so nothing is installed. Before this tool the
  maintainer saw DeepSeek write its own script to draw pages with headless Edge; inside the
  scripts' AppContainer Edge crashed and Windows showed its "Application Error" box. The tool
  starts the browser outside the container, with no console window and with Windows' crash boxes
  off for the child (its error mode is set around the start). One run dumps the page's DOM with the report in it, one
  takes the screenshot; about 1.2 s for a page here.
- The picture reaches the model in a user message right after the step's tool results, added to
  the request only (`pictures_as_user_message`, a middleware in `runtime_lg/agent.py`): an image in a
  tool message is accepted by DeepSeek (checked live) but not by every OpenAI-compatible API, and a
  user's image works wherever images do. The saved history keeps the result whole; the tab, the
  history replay and the hooks get its text and the number of pictures.
- The Design and Dashboard skills: look before saying it is done, fix what the report and the
  pictures show, look again.
- Tests: `tests/test_page_tools.py` (the tool end to end with a real Chromium where one is
  installed: overlap, text past the edge, a blocked load, the canvas variable in the picture, one
  board, errors), the middleware through a real agent in `tests/test_runtime_lg_agent.py`, and Edge
  on a real Windows runner in `tests/test_windows_real.py` (windows-more-checks.yml).

## Not verified
- Edge on a person's Windows machine (the runner's Edge is the CI check).
- A model with no image input: its provider would refuse the picture.

## Evals with the tool (DeepSeek, 2026-10-30, off-peak)
- **Design** (7 briefs, brief 07 a linked prototype):
  - 7 of 7 made and working; 0.26 USD in all.
  - Every run looked: 2 to 16 times, median 5.
  - Every run edited its pages after looking: 3 to 13 edits.
  - The checks found no script error, no overflow and no undeclared variable.
  - Links: brief 05 had 7 and brief 07 had 8, none broken.
  - Screenshots: no text over text, and no block runs into a footer, which is the fault the first
    run found on a poster.
  - The most looking was brief 07: 4 screens, 16 looks, 23 writes, 428 s, 0.063 USD.
- **Dashboard** (6 briefs):
  - 6 of 6 made and working; 0.14 USD in all.
  - Every run looked: 2 to 11 times.
  - No unknown name, no number typed into the page, and no script error.
  - Every figure that was checked was right.
- The skills are not changed. The audit log keeps only writes, not what each look reported, so a
  look that found nothing cannot be told from one whose fault was then fixed. "Two rounds are
  usually enough" stays as written.

## Follow-ups
- To learn what each look found, the eval would record each look's report.
