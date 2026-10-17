# workflows: fixed lists of low-autonomy steps, run by LangGraph

## Purpose
Owns what a workflow is (`spec.py`, `refs.py`), how it runs (`engine.py`), what it may touch
(`permissions.py`), the tool parameters its editor needs (`catalog.py`), drafting one from a
conversation (`solidify.py`) and a one-off test run (`testing.py`). Does not own the schedule
that fires a run or its stored history (`runtime_lg/scheduled_tasks.py`), the routes
(`web/routes/scheduled.py`) or any agent: a fixed run never contains one.

## Public interface
`BranchStep`, `LoopStep`, `Workflow`, `parse_workflow`, `walk`, `workflow_error` (the definition);
`RunOutcome`, `StepContext`, `StepRecord`, `WorkflowNotRunnable`, `WorkflowRun` (a run);
`granted_by`, `sites_in`, `summarize` (permissions); `describe_params`, `tool_description`
(catalog); `output_files`, `run_test`, `uses_browser` (test run); `DraftFailed`, `WorkflowDraft`,
`draft_workflow`, `revise_workflow` (drafting from a conversation: it takes the serialized
history, so this package does not import `runtime_lg`). Two other callers still import submodules (`workflows.spec`, `.permissions`):
`coordinator.py` (an invariant path) and `tools/bookkeeping/scheduled_tasks.py` (importing the package
there cycles); do not copy them.

## Depends on
`coscribe.needs_permission`, `coscribe.tools`.

## Invariants
- `engine`, `spec`, `refs` and `permissions` never import `code_runtime`, `runtime_lg` or
  `coordinator` (`docs/decisions/0005-code-is-a-second-runtime.md`, an import contract).
- A reference is a lookup, never an expression: nothing in `refs.py` evaluates code.
- Saving is the consent: a site or folder outside what `permissions.granted_by` lists stops a run.
- A test run stops before an approval step and writes no run history.
- `UNAVAILABLE_TOOLS` in `engine.py` only lists tools a run may not call; the import contract,
  not that list, is what keeps the code module out.

## Tests
`tests/test_workflow_spec.py`, `tests/test_workflow_engine.py`, `tests/test_workflow_permissions.py`,
`tests/test_workflow_catalog.py`, `tests/test_workflow_solidify.py`, `tests/test_workflow_testing.py`;
`tests/web/test_scheduled.py` covers runs through the server.

## Verify by hand
Drafting a workflow from a real conversation with a real model (`solidify`); a browser step
on a real Windows machine.

## Reviewed
2026-10-12 (pilot card; the sha is added when the card is first checked against a later change).
