# `routes/threads.py` router split per resource (shipped)

Why: #348 item 4. `threads.router` was 337 lines and complexity 60, the longest route builder after `scheduled`.

## Shipped
- `web/routes/threads.py`: `router(state)` now creates the `APIRouter` and calls eight groups in the
  original registration order: `_listing_routes` (list, status), `_group_and_lifecycle_routes` (groups,
  meta), `_delete_and_rename_routes`, `_task_and_draft_routes`, `_file_and_context_routes`,
  `_subagent_routes`, `_background_task_routes`, `_environment_and_messaging_routes`. The helpers
  `_threads_waiting_for_input`, `_thread_status` and `_thread_file` are module-level and take the state;
  the docx-review routes still receive `_thread_file`. Route bodies are unchanged.
  `tests/web_routes.txt` and `tests/openapi.json` are unchanged.
- `quality/baseline.json`: `long_functions` 37 to 36, `complex_functions` 22 to 21.

## Not verified
- `tests/web/` and the route and OpenAPI snapshots pass locally; the thread sidebar and file open were
  not exercised in the desktop app.

## Follow-ups
- Left over 300 lines: `create_app_lg` (invariant path, needs an independent review).
