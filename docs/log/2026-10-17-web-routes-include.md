# `web.app` fan-out 26 to 25 (shipped)

Why: #348 item 4, the last open row of the fan-out criterion (`web.app` imported 26 modules, the limit is 25).

## Shipped
- `web/routes/__init__.py` gains `include_routers(app, state)`, which registers the eight routers in
  the order `create_app_lg` used. `web/app.py` imports the package once instead of the eight route
  modules, so its fan-out goes from 26 to 19 and `create_app_lg` from 249 to 239 lines.
  `tests/web_routes.txt` and `tests/openapi.json` are unchanged.
- `quality/baseline.json`: the `fan_out` entry is gone.

## Not verified
- `tests/web`, the route and OpenAPI snapshots and the card tests pass locally; the server was not
  started on a Windows machine.
