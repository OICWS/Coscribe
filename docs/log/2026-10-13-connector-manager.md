# `ConnectorManager`: the connector closures leave `create_app_lg` (shipped)

Why: second of three pure moves (issue #146) that make `create_app_lg` a composition
root. The connector tools, their live connections and the rebuild of open
conversations could only be reached by building the whole FastAPI app.

## Shipped
- `web/connector_manager.py`: `ConnectorManager` holds `tools`, `connections`,
  `sign_in_tasks`, and the former closures `_session_extra_tools`, `_connector_tools`,
  `_disconnect_mcp_server_lg`, `_reconnect_stale_connector`,
  `_connect_and_register_mcp_server_lg`, `_refresh_all_sessions_extra_tools` as
  methods, bodies unchanged except state read from `self`. It takes `Settings`, the
  sessions mapping and `McpOAuth.auth_for`; it imports nothing from FastAPI.
- `web/app.py` builds it and fills `AppState` with its bound methods and its
  `connections` / `sign_in_tasks`, so no route module changes. The lifespan's startup
  connect writes to `connectors.tools` / `connectors.connections`.
- One-line exports so the new module adds no `deep_imports` entry: connector
  permission helpers, `prepare_for_connect` and `validate_mcp_config` in
  `tools/__init__.py`, `SecretError` in `runtime/__init__.py`, and a lazy
  `connect_one_mcp_server_lg` in `runtime_lg/__init__.py` (resolved on first use, like
  `connect_mcp_tools_lg`, so a user with no MCP servers still skips the adapter import).
- Ratchet: `web/app.py` 1,016 -> 864 lines, `create_app_lg` 650 -> 513 lines and
  complexity 73 -> 55, `fan_out` of `web.app` 32 -> 28, six `deep_imports` entries gone.
- `tests/web/test_connectors.py`: four tests build `ConnectorManager` without FastAPI.

## Not verified
- A real sign-in to a hosted connector (needs an account and a browser); the web tests
  that drive connect, disconnect and the OAuth routes through the app pass unchanged.
- Windows.
