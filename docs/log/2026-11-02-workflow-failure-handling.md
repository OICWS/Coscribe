# A workflow step says what happens when it fails (shipped)

Why: any failed step stopped the run. A site that didn't answer for a minute failed a monthly
task, one bad invoice stopped the other forty-nine, and no one heard of a failed run (#776,
batch 2; decision 0032).

## Shipped
- `workflow_spec`:
  - A work step's `on_failure`: retries with a wait, then stop, skip, or steps in its place
    (`OnFailure`, `failure_policy`); never retries on a step marked irreversible.
  - A loop's `on_item_failure`, and a workflow's `after_failure` steps (`Workflow.every_step`).
  - What later steps may read after a skipped or replaced step (`scope.py`, split from
    `spec.py`), and error locations inside both new lists (`locate.py`).
- `workflows`:
  - The engine routes each try, the skip, the steps in its place and a skipped item through the
    graph, so a pause during a retry resumes that try. The steps after a failed run never
    pause. What a tool, script, model or check step does moved to `step_work.py`.
  - Records carry `attempts` and `recovered`; the report lists recovered failures, retries and
    the steps after a failure, and a loop's report counts the items that worked.
  - A test run guards an irreversible step in a failed step's place, leaves out irreversible
    steps after a failure, and waits at most 5 seconds between tries. An agent that reads
    `failure` gets read-only tools. The drafter is told the new fields.
  - `compiled_graph` (`graph_view.py`): the nodes and edges LangGraph compiles a workflow to,
    for the editor's Compiled graph view (`POST /api/workflows/graph`).
- Frontend:
  - Canvas: a step's failure setting on its card, the steps in its place under "If it fails",
    a loop that skips items, the "After a failed run" frame; hovering a step highlights the
    steps it reads from and the ones that read it.
  - Quick edit: an "If it fails" section; the full editor sets steps in a step's place and the
    steps after a failed run. A Compiled graph view beside Detailed.
  - Run view and report: a recovered step in amber with how it was handled, the steps in its
    place nested under it, skipped items in amber, and "Failed without stopping the run".
- Tests: `tests/test_workflow_failures.py` (19), `lib/failureWords.test.ts`,
  `lib/dataFlow.test.ts`, and the e2e spec `workflow-failure-handling.spec.ts`.

## Not verified
- On a real Windows machine: a run that waits between tries while the app is closed and opened
  again (the try starts over after a restart, by design).

## Follow-ups
- Batches 3 to 5 of #776 (in `docs/plan.md`).
