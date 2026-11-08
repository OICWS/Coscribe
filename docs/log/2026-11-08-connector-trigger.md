# A task starts on something new in a connector (shipped)

Why: handling "each new email with this label" or "each new row in that database" meant a task
that ran every few minutes and kept its own list of what it had done (#850, part of #843;
decision 0039).

## Shipped
- A new kind in the task form, "When something new shows up in a connector": a connected
  connector's tool, its arguments, how often to ask, at most how many runs an hour, and which
  input each new item fills (`ConnectorTriggerFields.tsx`). "Check now" asks the tool once
  (`POST /api/mcp/check`) and lists what it has and its fields.
- The poll asks each due task's tool (`runtime_lg/connector_checks.py`); what was seen, what each
  item fills in and the limits (3 at once, 30 an hour by default) are `tools/bookkeeping/
  connector_items.py`. The first look takes everything as seen; an item that doesn't fit its
  inputs is listed on the task page with the reason and not tried again.
- Only a tool marked read-only, or one the person confirmed, is asked; a blocked one never is.
  Each check that found something or failed goes to the audit log (`trigger_check`).
- A run started this way says "New in <connector>" and keeps the item, shown under Details.
- `ScheduledRun` moved to `tools/bookkeeping/scheduled_run.py`, which brings `scheduled_tasks.py`
  from 964 to 909 lines.
- Tests: `tests/test_connector_trigger.py`, `tests/web/test_connectors.py` (the check route).

## Not verified
- A real Gmail, Notion or Linear connector: their answers' shapes and which tools they mark
  read-only. The tests use a fake connector tool.
- The form and the checks in the desktop app on Windows.

## Follow-ups
- A local webhook that starts a run (#850, its own decision record and an independent review).
