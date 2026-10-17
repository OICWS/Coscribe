# `build_docx_tools` split into five builders (shipped)

Why: #348 item 4. `build_docx_tools` was 357 lines, over the 300-line exit criterion.

## Shipped
- `tools/office/docx/tools.py`: the 8 inline tools are grouped, in order, into five builders of
  under 100 lines; `build_docx_tools` concatenates their lists with the read, structure and review
  tools. Bodies, docstrings (the tool schemas) and the tool order are unchanged (compared by name
  before and after).
- `quality/baseline.json`: `long_functions` 40 to 39.

## Not verified
- The schema snapshot is checked by CI only (it fails in a cloud session on main, #252). The docx
  tests, goldens and the card test pass locally.
- #343 changes the review tools; this PR does not touch `_review.py` or `_docx_review_tools`.

## Follow-ups
- Left over 300 lines: `create_app_lg`, `build_browser_tools`, the two routers.
