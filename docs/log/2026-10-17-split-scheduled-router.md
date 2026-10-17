# `routes/scheduled.py` router split per resource (shipped)

Why: #348 item 4. `scheduled.router` was 347 lines and complexity 62, the longest route builder.

## Shipped
- `web/routes/scheduled.py`: `router(state)` now creates the `APIRouter` and calls six groups in the
  original registration order: `_workflow_routes` (validate, permissions), `_task_routes` (list,
  create, update, patch), `_run_control_routes` (run now, stop, investigate), `_approval_routes`
  (answer), `_retry_routes`, `_note_and_lifecycle_routes` (notes, pause, resume, delete). The two
  helpers `answer` and `retry` share moved into `_run_reopeners`; `_waiting_permission` is module-level.
  Route bodies are unchanged. `tests/web_routes.txt` and `tests/openapi.json` are unchanged.
- `quality/baseline.json`: `long_functions` 38 to 37, `complex_functions` 23 to 22.

## Not verified
- `tests/web/test_scheduled.py`, `test_web_routes.py`, `test_openapi_snapshot.py` and the card test
  pass locally; no scheduled task was run in the desktop app.

## Follow-ups
- Left over 300 lines: `threads.router` and `create_app_lg`.
