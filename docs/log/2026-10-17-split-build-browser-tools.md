# `build_browser_tools` split into four builders (shipped)

Why: #348 item 4. `build_browser_tools` was 354 lines, over the 300-line exit criterion.

## Shipped
- `tools/web/browser.py`: the 14 tools are grouped into four builders (navigation, input, waiting,
  page) that each take the shared `call` (and the workspace scope, where a tool reads downloads or
  uploads). `call` moved to `_browser_call` and `wait_limit` to the module-level `_wait_limit`;
  `build_browser_tools` assembles the same read, act and evaluate lists in the original order.
  Tool bodies and docstrings (the tool schemas) are unchanged apart from the `_wait_limit` name; the
  tool order was compared by name before and after.
- `quality/baseline.json`: `long_functions` 39 to 38, `complex_functions` 24 to 23.

## Not verified
- The schema snapshot is checked by CI only (it fails in a cloud session on main, #252).
  `test_browser_tool.py` and the card tests pass locally. The browser tools were not run against a
  real page in the desktop app.

## Follow-ups
- Left over 300 lines: `create_app_lg` and the two routers.
