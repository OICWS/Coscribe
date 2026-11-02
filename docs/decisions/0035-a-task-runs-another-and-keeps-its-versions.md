# 0035: A task runs another task as a step, and keeps every version it was saved as

Status: proposed (2026-11-02, kurtosisOC; needs the maintainer's acceptance). Builds on 0032,
0033 and 0034. Issue #776, batch 5.

## Context
Two tasks that share work (fetch the month's sales, then report or reconcile) each held a copy
of the same steps, and a fix to one never reached the other. A saved task also kept only its
latest definition: an edit that broke it could not be undone, and a run did not say which
definition it ran.

## Decision
- **A run-task step** (`kind: "run_task"`) runs another workflow task by its id: `inputs` gives
  the values the called task asks for (text with references; one left out takes its default),
  and `save_as` gets its results: every name its top-level steps saved. It may say what happens
  when it fails, like a tool step. A new kind changes nothing an older workflow says, so the
  format keeps its version.
- **The called task runs as a run of its own** inside the step, on its own checkpoint thread in
  the same store, with its own approval mode, autonomy, memory (kept when its part completes)
  and steps after a failure. Its pauses pause the caller; its step records are the caller's,
  as `<step>/<its step>`. A retry of the run-task step goes on from where the called task
  failed, not from its start, so nothing it already sent is sent twice.
- **Calls nest at most 3 deep and never in a cycle.** Saving a task checks both, across every
  task that calls it or that it calls, and that each called task exists, has a workflow, is
  given every input it needs and has the results the caller reads. A run checks again, since a
  called task can change after its caller was saved. Pausing a task stops its schedule, not its
  use as a step.
- **The called task's permissions are its own.** The folders and sites a caller's run may use
  include those the called tasks' steps name or were allowed; the permissions card lists them
  under each called task's name, and one allowed while a called step waits is granted to the
  called task.
- **Every save keeps a version** (`state_dir/task_versions/<id>.json`, the latest 50, deleted
  with the task): its number, when, how (`created`, `edited`, `conversation`, `restored`) and
  the workflow. A task saved before versions starts its history at version 1 when first
  changed. The task page lists them, compares one with the current step by step, and restores
  one in a click, which saves it as a new version.
- **A run records the versions it ran** (`versions`, usually one; a retry after an edit adds
  the newer), and for each called task its name, version and definition (`called`), so the run
  view shows the called steps as they were.

## Consequences
- The editor, quick edit, simple view, permissions card, run view and run report know the new
  step; the drafter and reviser are told which tasks can be called, with their inputs and
  results.
- A run still reads its task's current definition at each action, as before; versions record
  it, they do not pin it.
- Out of scope: running a called task in parallel, passing a task's memory between tasks, and
  versions of a task's schedule or settings.
