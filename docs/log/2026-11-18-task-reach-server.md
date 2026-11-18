# The server says what a scheduled task can reach (partly shipped)

Why: decision 0048 has a task show what it can reach and pick its folder inputs from it, with a
folder outside allowed on the spot. This is the server part; the task form follows.

## Shipped
- `GET /api/scheduled-tasks/{id}/reach`: the task's workspace and its folders, Settings' Allowed
  folders with their access, and the folders allowed for this task only (`web/routes/task_reach.py`).
- `POST` and `DELETE /api/scheduled-tasks/{id}/folders`: allow a folder on this computer for the
  task's runs only, audited as `allow_task_folder`, or take it back.
- `POST /api/reach/check`: where a folder an input names falls (workspace, task or allowed), from
  the workspace's folder when relative, whether a run may write there and whether it exists. A task
  not saved yet is checked against the workspace it will use.
- Tests: `tests/web/test_scheduled_reach.py`.

## Not verified
- Windows paths (a drive letter, a share, a different case) against a real Windows machine; CI's
  Windows job runs the tests.

## Follow-ups
- The task form: a "What this task can reach" block, folder inputs picked from the reach, and the
  card for a folder outside it (Only this task, Allow everywhere, Pick another folder).
