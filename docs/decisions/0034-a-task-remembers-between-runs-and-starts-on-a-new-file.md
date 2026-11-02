# 0034: A task remembers between runs, and starts on a schedule of minutes or a new file

Status: proposed (2026-11-02, kurtosisOC; needs the maintainer's acceptance). Builds on 0031 and
0033. Issue #776, batch 4.

## Context
Every run started from nothing. A task that should handle only what is new since last time (new
rows in a sheet, invoices not yet filed) had to keep its own list in a file, and nothing could
start it except the clock or a person. A task that checks every few minutes would also notify
the person each time it found nothing.

## Decision
- **A workflow declares what it remembers** (`memory`: at most 20 entries, each a name, a label,
  a type of text, number, date or list, and a value the first run reads). Steps read them as
  `{{memory.<name>}}`, and `{{run.started_at}}` and `{{run.date}}` say when this run started.
  The names `memory` and `run` are then reserved; a workflow without `memory` may still use them.
- **A remember step** (`kind: "remember"`) sets one entry to a value, checked against its type.
  It is kept only when the whole run completes: a failed or stopped run keeps nothing, and later
  steps of the same run still read the old value. A value holds at most 20,000 characters; a list
  over that drops its oldest items, so a list of what was handled never fails a run by growing.
- **What a task remembers lives beside the task** (`state_dir/task_memory/<id>.json`, deleted
  with it). The task page shows each value, which run kept it and when, and the person can
  correct or clear it; a cleared value is read as the starting value again.
- **A check can end a run quietly** (`otherwise: "end"`, only at the top level): the run
  completes with "nothing to do" and the remaining steps are not reached. Such a run sends no
  notification, and a row of them in the run list is kept as its latest, counting the ones it
  stands for (`quiet`), with their threads deleted.
- **Every few minutes** (`kind: "every"`, 5 to 1,440 minutes) runs a task that far apart, for
  polling with memory. No webhooks: the app runs on the person's computer.
- **A new file in a folder** (`kind: "folder"`, with `folder`, `pattern` and the file `input` it
  fills) starts one run per file. The folder is added to the task's folders. The first look takes
  what is there as seen; a file counts once it has stopped changing for 5 seconds, partial
  downloads and hidden files are skipped, at most 5 start per check, and a file replaced by a newer
  one counts again. A paused task starts from what is there when it resumes.
- **A test run reads the task's memory and keeps nothing**: it reports what it would have kept.
- Memory is a workflow's, and a folder task needs a file input, so the form offers both new kinds
  only for workflow tasks.

## Consequences
- The editor has the memory section, the remember step and the check's "otherwise" in the full
  editor and quick edit; the schedule form has the two new kinds; the run report lists what was
  kept and where a run ended quietly.
- A workflow without memory or the new kinds runs as before; no new version.
- Out of scope: webhooks and connector events as triggers, a drafter that proposes a trigger,
  and these kinds in the agent's own `create_scheduled_task` tool.
