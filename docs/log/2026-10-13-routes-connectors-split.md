# web/routes/connectors.py is a package, one module per resource (shipped)

Why: `connectors.py` was 463 lines with one 386-line `router()` (issue #145, part of #150); the
second half after the settings split.

## Shipped
- `web/routes/connectors/` replaces `connectors.py`. Code moved as is, one module per resource:
  `catalog` (`/api/mcp/catalog`), `oauth_apps` (`/api/mcp/oauth-apps*`), `signin` (the OAuth
  redirect and signing in again), `servers` (list, add, remove), `permissions`, `maintenance`
  (latest npm version, reconnect, bump version). `_shared.py` holds `make_begin_oauth_sign_in`, the
  sign-in starter that `signin` and `servers` both use. `__init__.py` keeps `router(state)`, so
  `web/app.py` does not change. Largest module: `servers.py`, 196 lines.
- `quality/baseline.json`: the `connectors.py` entries are replaced by the same offenders under
  their new module names. `router` falls from 386 lines / complexity 71 to 142 / 24 (`servers`).
  `deep_imports` has four more entries than before, because the modules that each import
  `tools.mcp`, `runtime_lg.mcp_oauth` or `tools.connector_permissions` now list it separately.
- `tests/web_routes.txt`, `tests/tool_schemas.txt` and `tests/openapi.json` are unchanged; no test
  file is changed.

## Not verified
- Windows: ran on Linux only.

## Follow-ups
- None for #145.
