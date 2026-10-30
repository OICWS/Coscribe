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
- Drawn in the computer's own Edge or Chrome, headless, with a throwaway profile: Edge ships with
  every Windows, so nothing is installed. One run dumps the page's DOM with the report in it, one
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
- A model using it in a real conversation: the Design and Dashboard evals run again off-peak.

## Follow-ups
- Re-run both evals with the tool and record whether the model looks and fixes what it sees.
