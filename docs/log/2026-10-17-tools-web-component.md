# `tools.web` is a component (shipped)

Why: issue #348 item 1. The browser, web search, HTTP and image tools are the tools that reach
the internet; they sat as five loose modules in `tools/`.

## Shipped
- A pure move: `browser.py`, `websearch.py`, `http_request.py`, `images.py` and
  `_licensed_image_search.py` are now `tools/web/`, with an `__init__.py` (`__all__` of the ten
  names other components use), a card and a `components.toml` entry. Tool schemas and routes are
  unchanged; the only snapshot text that moved is a path in one route's OpenAPI description
  (`tests/openapi.json`, "see tools/web/browser.py").
- `tools/__init__.py` binds `.web` first (with `# isort: split`) because `workflows.testing`
  imports `BROWSER_RUNS` from `coscribe.tools` while `scheduled_tasks` is still importing
  `workflows`.
- `deep_imports` stays 37; ratchet keys for the moved files were renamed, no number moved.

## Not verified
- The full suite passes locally except `test_tool_schema_snapshot` (the same failure as on `main`
  in cloud containers, #252); the web tests ran against a stub `web/static/index.html`.
- The browser tools were not run against a real page.

## Follow-ups
- The bookkeeping tools (#348 item 1).
