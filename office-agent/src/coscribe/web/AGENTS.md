# web: the local FastAPI server, its routes and the shared state behind them

## Purpose
Owns the server process: the app factory and the `coscribe-web` entry point (`app.py`), the
first-run setup page (`setup_app.py` with `create_setup_app`), the objects every route shares (`state.py`), one router
module per area under `routes/` (`ws.py` the chat and browser sockets; `threads.py`, `files.py`,
`skills.py`, `scheduled.py`, `internal.py`, `slides.py` the Slides panel's reads, `artifacts.py` the Artifacts page's list, thumbnails and opening (`artifact_adoption.py` registers what conversations created); `settings/` and `connectors/` one module per
resource), request bodies (`schemas.py`), the connector catalog and the live connectors
(`connector_catalog.py`, `connector_manager.py`), the provider catalog, the loop that fires due
wakes and scheduled tasks (`scheduler.py`), background events for the tray (`background_events.py`),
the browser panel (`browser_panel.py`, `browser_detect.py`) and the `Host`/`Origin` guard on every request and socket (`local_guard.py`). Does not own a conversation's turns
or approvals (`conversation/`), the agent (`runtime_lg/`) or the UI (`frontend/`, built into `static/`).

## Public interface
None re-exported: `__all__` is empty. Entry points: `create_app_lg` and `main` in `app.py`
(`coscribe-web`), `create_setup_app` (the setup page's app) in `app.py`. Route modules are reached through
`create_app_lg`; tests import them to patch (`tests/web/helpers.py` holds the shared fakes).

## Depends on
`coscribe`, `coscribe.code_runtime`, `coscribe.config`, `coscribe.conversation`,
`coscribe.coordinator`, `coscribe.runtime`, `coscribe.runtime_lg`, `coscribe.tools`,
`coscribe.workflows`.

## Invariants
- `web` is the only package that imports FastAPI, Starlette or uvicorn (import contract). The one
  upward import, `web.app -> cli`, is listed in `pyproject.toml`; do not add another.
- `app.py` opens the network listener, an invariant path (`office-agent/CLAUDE.md`): it binds
  `127.0.0.1` by default and a change there needs an independent review. `app.py` is also a hot
  file: look at the open pull requests before editing it.
- A new WebSocket event is added to `conversation/wire.py` first; the tests check every payload
  against it. A route's request and response shapes are pinned by `tests/test_openapi_snapshot.py`.
- Every request and WebSocket passes `LocalOnlyGuard` (`local_guard.py`): `Host` and a browser `Origin` must be
  loopback or in `COSCRIBE_ALLOWED_HOSTS`. A new app (like the setup app) adds it; tests get `testserver` from
  `tests/conftest.py`. The real app also passes a launch token: a WebSocket and every request that
  is not a read must carry it, so a new GET route must change nothing
  (`tests/web/test_launch_token.py` lists the audited ones); tests use `TokenClient` from
  `tests/web/helpers.py`.
- Hosted connectors sign in once in the user's own browser; the catalog lists no shared client
  secret (`docs/decisions/0004-connectors-sign-in-once-in-the-browser.md`).
- A new route test goes into the file of its domain under `tests/web/`, shared fakes into
  `tests/web/helpers.py`.

## Tests
`tests/web/test_*.py` by domain (chat, threads, connectors, settings, skills, scheduled,
subagents, internal), `tests/test_web_routes.py`, `tests/test_openapi_snapshot.py`,
`tests/web/test_local_guard.py`, `tests/web/test_launch_token.py`, `tests/test_setup_app.py`, `tests/test_browser_panel.py`, `tests/test_browser_detect.py`;
`frontend/tests/e2e/` runs the UI against a live server.

## Verify by hand
The first-run setup page on a clean Windows profile; the browser panel and a connector sign-in in
the desktop app; the tray notification for a finished background task.

## Reviewed
2026-10-14 (first card).
