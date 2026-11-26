# tools.web: the browser, web search, HTTP requests and image search

## Purpose
Owns the tools that reach the internet for the model: the browser tools and the `BrowserHost`
that drives the desktop app's built-in browser (`browser.py`; the tab tools, multi-page reads and
what results say about pages in `_browser_pages.py`; forms, several actions in one step and
waiting for one of several texts in `_browser_forms.py`; dragging and the AI's own clipboard in
`_browser_moves.py`; a table or list to a CSV and the page to a PDF in `_browser_data.py`; the
page as a picture, a click by position and the text by a label in `_browser_look.py`),
`web_search` and `read_web_page` (`websearch.py`; the free engines asked at once under one
deadline, and what a failed search says, in `_search.py`), `http_request` with secret substitution
(`http_request.py`) and licensed image search and download (`images.py`,
`_licensed_image_search.py`). Does not own the browser panel or its routes (`web/`), the proxy
setting (`runtime/proxy.py`) or secret storage (`runtime/`).

## Public interface
`build_browser_tools`, `build_websearch_tools`, `build_http_tools`, `build_image_tools`,
`BrowserHost`, `BrowserUnavailableError`, `BROWSER_HOST`, `browser_run`, `SCREENSHOT_FOLDER`,
`page_screenshot`. Import them from `coscribe.tools.web`.

## Depends on
`coscribe.needs_permission`, `coscribe.runtime`, `coscribe.tools._workspace`.

## Invariants
- A secret's value never reaches the model: `http_request` substitutes it after the model's call
  and blanks it in the output (`docs/decisions/0003-secrets-promise.md`).
- Browser commands go to the desktop app's own browser through the internal route; there is no
  remote-debugging port.
- Tool schemas are fixed and snapshotted (`tests/tool_schemas.txt`).
- A search or page read that can't connect fails within seconds and says why (no proxy, a proxy
  that reaches nothing, a site the network blocks); a search that reached no engine is not
  retried, and its verdict is reused for 30 s per proxy (`_search.py`).
- A conversation's network setting (`runtime.NetworkGuard`, Edit workspace > Sites) is checked
  at each call, and on every request of `read_web_page`, `download_image` and `http_request`, so a
  redirect can't leave the allowed domains; the browser's steps are checked by the desktop app
  against `network_sites`, and asks, allows or refuses each site from `browser_sites`, the
  workspace's browser level per site (decision 0050; `tests/test_network_access.py`).

## Tests
`tests/test_browser_tool.py`, `tests/test_browser_data_tool.py`, `tests/test_browser_look_tool.py`,
`tests/test_websearch_tool.py`, `tests/test_http_request.py`, `tests/test_images_tool.py`,
`tests/test_licensed_image_search.py`, `tests/test_proxy.py`, `tests/test_network_access.py`.

## Verify by hand
The browser tools against a real page in the desktop app; a web search and an image download
behind a proxy.

## Reviewed
2026-10-17 (first card).
