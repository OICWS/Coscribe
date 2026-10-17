# tools.web: the browser, web search, HTTP requests and image search

## Purpose
Owns the tools that reach the internet for the model: the browser tools and the `BrowserHost`
that drives the desktop app's built-in browser (`browser.py`), `web_search` and `read_web_page`
(`websearch.py`), `http_request` with secret substitution (`http_request.py`) and licensed image
search and download (`images.py`, `_licensed_image_search.py`). Does not own the browser panel
or its routes (`web/`), the proxy setting (`runtime/proxy.py`) or secret storage (`runtime/`).

## Public interface
`build_browser_tools`, `build_websearch_tools`, `build_http_tools`, `build_image_tools`,
`BrowserHost`, `BrowserUnavailableError`, `BROWSER_HOST`, `BROWSER_RUNS`, `SCREENSHOT_FOLDER`,
`page_screenshot`. Import them from `coscribe.tools.web`.

## Depends on
`coscribe.needs_permission`, `coscribe.runtime`, `coscribe.tools._workspace`.

## Invariants
- A secret's value never reaches the model: `http_request` substitutes it after the model's call
  and blanks it in the output (`docs/decisions/0003-secrets-promise.md`).
- Browser commands go to the desktop app's own browser through the internal route; there is no
  remote-debugging port.
- Tool schemas are fixed and snapshotted (`tests/tool_schemas.txt`).

## Tests
`tests/test_browser_tool.py`, `tests/test_websearch_tool.py`, `tests/test_http_request.py`,
`tests/test_images_tool.py`, `tests/test_licensed_image_search.py`, `tests/test_proxy.py`.

## Verify by hand
The browser tools against a real page in the desktop app; a web search and an image download
behind a proxy.

## Reviewed
2026-10-17 (first card).
