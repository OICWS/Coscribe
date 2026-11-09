# 0039: A task starts on something new in a connector

Status: proposed (2026-11-08, OICWS; agreed with the maintainer in the project thread). Narrows
0034 (a task may now start on a connector's new items). Issue #850, part of #843. A local webhook
is 0040.

## Context
A task could start on the clock, by hand or on a new file. Handling "a new email with this label"
or "a new row in that database" meant running every few minutes, keeping a list of what was done
in memory and handling a batch per run. Coscribe listens only on 127.0.0.1 and connectors (MCP)
answer only when asked, so no service can push an event in.

## Decision
- **A new trigger kind, `connector`**: a connected connector's tool, its arguments and how often
  to ask (5 to 1,440 minutes). Each item in the answer that wasn't there before starts one run.
  The answer is a list, or an object holding one (`messages`, `items`, `results` and the like).
- **What is new**: an item is known by a field like `id`, `messageId` or `url`, else by a
  fingerprint of all of it. The first look takes what is there as seen, as a folder task does; a
  task that asks something else, or is paused and resumed, starts over. Seen keys are kept even
  when an item leaves the answer.
- **What it fills in**: each input takes a field of the item by the person's pick (a dotted path,
  the whole item, or its default), else the field named like it, checked against the input's
  type. An item that doesn't fit, or is over 64 KB, starts no run: the task page lists it with the
  reason, and it is not tried again. The run keeps the item, shown under Details.
- **Limits**: at most 3 runs from new items going at once (so at most 3 start per check) and 30
  an hour (the task can say 1 to 120). Items over a limit wait for later checks.
- **Only a read-only tool is asked unattended**: one its connector marks `readOnlyHint`, or one
  the person confirmed in the task form. A tool blocked in Settings > Connectors is never asked.
  Each check that found something or failed is in the audit log (`trigger_check`).
- **Only the person turns it on**, in the task form, for a task with steps. The agent's
  `create_scheduled_task` and the drafter don't offer it. The item is outside content; the run
  keeps the task's autonomy and permissions.

## Consequences
- `ScheduledRun` moved to `scheduled_run.py` and gained `event`; runs started this way say "New
  in Gmail". `/api/mcp/check` asks a tool once for the form; `/api/tools` says which connector
  tools are read-only.
- Out of scope: internet webhooks, one run for a batch of items, a drafter proposing this.

Retired wording: "webhooks and connector events as triggers"
