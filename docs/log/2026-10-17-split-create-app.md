# `web/app.py` create_app_lg trimmed (shipped)

Why: #348 item 4. `create_app_lg` was 381 lines and complexity 33, the largest function left in `web/`.

## Shipped
- `web/app.py`: the lifespan moved into `_make_lifespan`, the MCP connect-with-timeout block into
  `_start_mcp_connect`, and the provider listing into module-level `_providers_info(settings)` and
  `_configured_models(settings)`. Behavior, the listener binding and the startup order are unchanged;
  the tests that patch `MCP_STARTUP_TIMEOUT_SECONDS`, `poll_due_wakes` and `poll_due_scheduled_tasks`
  still patch module names read at call time.
- `quality/baseline.json`: `create_app_lg` 381 to 249 lines, complexity 33 to under the limit.

## Not verified
- `tests/web/` and the route and OpenAPI snapshots pass locally; the desktop app was not started and
  a slow MCP server at cold start was not tried on Windows.

## Follow-ups
- `create_app_lg` is still 249 lines (session factory, skills scan, thread deletion closures); a later
  step can turn them into a small class. Left over 300 lines: `_decide_action_request`.
