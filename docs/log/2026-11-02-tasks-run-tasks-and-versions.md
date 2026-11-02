# A task runs another task as a step, and keeps every version it was saved as (shipped)

Why: two tasks that share work each held a copy of the same steps, a fix to one never reached
the other, and an edit that broke a task could not be undone or traced to the runs it affected
(#776, batch 5; decision 0035).

## Shipped
- `workflow_spec`: `RunTaskStep` (`kind: "run_task"`: `task`, `inputs`, `save_as`, failure
  handling like a tool step), `MAX_TASK_DEPTH` (3) and `task_results` (the names a workflow's
  top-level steps save). Unused names left `__all__`.
- `workflows/run_task.py`: the called task runs as a `WorkflowRun` of its own on the thread
  `<caller>~<step>~<task id>`, in the caller's checkpointer, with its own approval mode and
  memory (kept when it completes; a test run keeps nothing). Its records are the caller's as
  `<step>/<its step>`; its pauses pass up through `interrupt` keyed by its checkpoint, and a
  retry of the step goes on from where it failed. `permissions.allowed_to_run` adds the called
  tasks' folders and sites to what a caller's run may use; the report lists the tasks a run ran
  (`tasks`); the drafter and reviser are told which tasks a step can run.
- `tools.bookkeeping`: `task_versions.py` (one version per save that changes the workflow, the
  latest 50) and `task_calls.py` (on save: the task exists and has steps, every input it needs
  is given, the results a caller reads exist, no cycle, at most 3 deep across every stored task).
  A run records `versions` and `called`.
- Routes: `GET /api/scheduled-tasks/{id}/versions`, `POST .../versions/{n}/restore` (refused when
  the restored steps' calls no longer work); the task list gives each task's `version` and
  `results`; answering, granting and retrying reach a called task's step.
- Frontend: the run-task step in the full editor (`RunTaskEditor.tsx`), the add-step menu,
  quick edit, the canvas and the simple view; the run view nests the called task's steps
  (`lib/calledRun.ts`); the report and permissions card name each called task; the task page's
  versions with Compare and Restore (`TaskVersionsSection.tsx`, `lib/versionDiff.ts`), and each
  run's version in the run list.
- Tests: `tests/test_workflow_run_task.py` (18), `tests/web/test_task_versions_web.py`,
  `lib/versionDiff.test.ts`, and the e2e spec `workflow-tasks-and-versions.spec.ts`.

## Not verified
- On a real Windows machine with a real model: a called task with browser steps, and a draft
  from a conversation that proposes a run-task step.

## Follow-ups
- Running called tasks in parallel, and versions of a task's schedule and settings, are left out
  (decision 0035).
