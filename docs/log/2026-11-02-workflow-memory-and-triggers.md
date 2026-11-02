# A task remembers between runs, ends quietly with nothing to do, and runs every few minutes or on a new file (shipped)

Why: every run started from nothing and only the clock or a person could start one, so a task
that handles only what is new had to keep its own list, and one that checks often notified the
person every time it found nothing (#776, batch 4; decision 0034).

## Shipped
- `workflow_spec`: `memory` (`MemoryEntry`, at most 20), `RememberStep`, a check's
  `otherwise: "end"` (top level only); `memory_value` checks a value against its type and keeps
  a list under 20,000 characters by dropping its oldest items; `remembered_values` is what a run
  reads as `memory.*` and `run.*`.
- `workflows`: the remember step (`remember_steps.py`) stages values in `RunOutcome.remembered`;
  a check that ends the run quietly sets `RunOutcome.ended`. The report lists what was kept
  (`remembered`, with labels) and where the run ended (`ended`). A test run reads the task's
  memory and says what it would keep (`would_remember`). The drafter is told the step and memory.
- `tools.bookkeeping`: `schedule_rule.py` (moved out of `scheduled_tasks.py`) with the `every`
  and `folder` kinds; `task_memory.py` and `folder_watch.py`, reached as a store's `memory` and
  `folders`. A finished run keeps its values; quiet runs fold into the latest (`quiet`), their
  threads deleted; deleting a task deletes both.
- Runs: each poll starts one run per new, finished file (source `file`, the path as the input),
  at most 5 a check; a quiet run sends no notification. Routes: `GET` and
  `PUT /api/scheduled-tasks/{id}/memory[/{name}]`, and `watch` on create and update.
- Frontend: the memory section and remember step in the full editor and quick edit, the check's
  "If they don't hold", the schedule form's two new kinds (`ScheduleFields.tsx`), the task page's
  remembered values with Edit and Clear (`TaskMemorySection.tsx`), "Nothing new · N checks" in
  the run list, and the run view's and report's new lines.
- Tests: `tests/test_workflow_memory.py` (16), `tests/test_task_triggers.py` (5),
  `tests/web/test_task_memory_web.py`, `lib/memoryWords.test.ts` (6), and the e2e spec
  `workflow-memory-and-triggers.spec.ts`.

## Not verified
- On a real Windows machine: a folder on OneDrive or a network share, a file arriving while the
  app is closed, and a browser download landing in the watched folder.

## Follow-ups
- The drafter doesn't propose a trigger, and the agent's `create_scheduled_task` tool doesn't
  offer the new kinds.
- Batch 5 of #776 (in `docs/plan.md`).
