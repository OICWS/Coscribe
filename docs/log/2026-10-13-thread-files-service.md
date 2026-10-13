# `ThreadFiles`: a thread's sidecar files leave `create_app_lg` (shipped)

Why: `create_app_lg` in `web/app.py` was a 731-line closure that could only be reached
by building the whole FastAPI app. The first of three pure moves (issue #146) takes the
thread-file closures out, as a class that is built with `Settings` alone.

## Shipped
- `web/thread_files.py`: `ThreadFiles` holds the title and workspace sidecar paths, the
  workspace sidecar read and write, a scheduled run's workspace and folders, and
  `resolve_folders`. The bodies are the closures' bodies with `settings` read from
  `self`. `delete` is the file part of `_delete_thread_data` (task list, sidecars,
  session environments, messaging allowances), so the app no longer imports those two
  stores.
- `web/state.py`: `AppState.thread_files` replaces `read_workspace_sidecar`,
  `write_workspace_sidecar` and `title_sidecar_path`; `routes/threads.py`, `scheduled.py`
  and `ws.py` read them from it.
- `tools/__init__.py` exports `MessagingStore` and `parse_run_thread_id`, and
  `runtime/__init__.py` exports `SessionEnvironments`, so the new module adds no
  `deep_imports` entry.
- Ratchet: `web/app.py` 1,100 -> 1,016 lines, `create_app_lg` 731 -> 650 lines and
  complexity 92 -> 73; one `deep_imports` entry gone. `fan_out` of `web.app` stays 32
  (it gains `thread_files`, loses `tools.conversations`); it drops with parts 2 and 3.
- `tests/web/test_threads.py`: five tests build `ThreadFiles` in `tmp_path` with no
  FastAPI.

## Not verified
- Windows: sidecar paths are plain `Path` joins, as before.

## Follow-ups
- Parts 2 and 3 of #146: `ConnectorManager`, then `Scheduler`.
