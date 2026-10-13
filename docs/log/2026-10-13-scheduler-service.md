# `Scheduler`: the wake and scheduled-task loop leaves `create_app_lg` (shipped)

Why: last of three pure moves (issue #146) that make `create_app_lg` a composition root.
The loop that fires due wakes and scheduled tasks, announces how runs ended and sweeps
orphaned run conversations could only be reached by building the whole FastAPI app.

## Shipped
- `web/scheduler.py`: `Scheduler` holds `wake_poll_loop`, `poll_scheduled_tasks_once`,
  `announce_run`, `execute_and_announce`, `track_background`, `delete_run_threads` and
  `sweep_orphaned_run_threads`, bodies unchanged except state read from `self`. `start()`
  creates the loop task and `stop()` cancels it and every tracked background run, which is
  what the lifespan did inline. It takes `Settings`, the sessions mapping, the event bus,
  the session getter, `_delete_thread_data` and the checkpointer as arguments, and the two
  poll functions too, so a test (or the app's existing tests that patch them on
  `web.app`) chooses them.
- `web/app.py`: builds it, the lifespan calls `sweep_orphaned_run_threads`, `start` and
  `stop`; `AppState` gets its bound methods, so no route changes.
  `_delete_thread_data` stays in the app (it needs the checkpointer and the open sessions).
- `tools/__init__.py` exports `ScheduledRun` and `SCHEDULED_THREAD_PREFIX`.
- Ratchet: `web/app.py` 854 -> 715 lines (off the file-size list), `create_app_lg` 513 -> 381 lines and
  complexity 55 -> 33, the lifespan no longer a long function.
- `tests/web/test_scheduled.py`: four tests build `Scheduler` without FastAPI.

## Not verified
- A scheduled task firing at its real time in the desktop app (needs a running
  desktop and a clock); the web tests that drive runs, wakes and the sweep pass unchanged.
- Windows.
