# workflows: fixed lists of low-autonomy steps, run by LangGraph

## Purpose
Owns how a workflow runs (`engine.py`, and what a step does when it fails, decision 0032; `step_work.py` what a tool, script, model or check step does; `graph_view.py` the graph a workflow compiles to, for the editor; `model_step.py` gets a model to return a step's
fields; `agent_step.py` runs an agent step through an injected runner; `report.py` a run's report, decision 0030; `healing.py` the agent that heals a failed browser step when the task's autonomy allows it; `heal_revision.py` the revision a run's heals propose; `run_task.py` a step that runs another task, decision 0035; `parallel.py` a step that runs lanes at the same time, decision 0036; `overview.py` the sentence the simple view opens a task with, decision 0037; `added_steps.py` the steps a run adds when a step fails, decision 0042; `routing.py` which way a run goes from a node), what it may touch (`permissions.py`), the tool parameters its editor needs (`catalog.py`), drafting one from a
conversation (`solidify.py`) and a one-off test run (`testing.py`). Does not own the schedule
that fires a run or its stored history (`runtime_lg/scheduled_tasks.py`), the routes
(`web/routes/scheduled.py`) or any agent: an agent step (decision 0028) runs through
`StepContext.run_agent`, which `conversation` supplies; without one `preflight` refuses it.

## Public interface
`BranchStep`, `ChoiceStep`, `LoopStep`, `Workflow`, `parse_workflow`, `walk`, `workflow_error` (the definition, re-exported from `workflow_spec`, where it lives);
`AgentCall`, `AgentReply`, `AgentRequest`, `AgentRunner` (what an agent runner takes and returns);
`RunOutcome`, `StepContext`, `StepRecord`, `WorkflowNotRunnable`, `WorkflowRun` (a run);
`brings_outside_content`, `granted_by`, `sites_in`, `summarize`, `untrusted_agent_steps`, `called_permissions`, `allowed_to_run` (permissions); `TaskSource` (where a run finds the tasks its steps run), `callable_tasks` (what the drafter is told it can run); `describe_params`, `tool_description`
(catalog); `ask_connector` (a connector tool's answer as a value, or why it gave none); `output_files`, `run_test`, `uses_browser` (test run); `run_report` (what a run did, from its step records); `compiled_graph` (the nodes and edges LangGraph compiles a workflow to); `answer_problem`, `paused_at`, `wake_due` (a run paused at an ask or wait step, decision 0033); `write_overview` (a task's one-sentence overview, decision 0037); `heal_fixes`, `heals_to_revise` (the saved arguments a run's heals would change, and the heals a revision has to be drafted for); `added_fix` (a run's added steps as their step's `on_failure: steps`, decision 0042); `DraftFailed`, `WorkflowDraft`,
`draft_workflow`, `revise_workflow` (drafting from a conversation: it takes the serialized
history, so this package does not import `runtime_lg`).

## Depends on
`coscribe.needs_permission`, `coscribe.tools`, `coscribe.workflow_spec`.

## Invariants
- Nothing here (or in `coscribe.workflow_spec`) imports `code_runtime`, `runtime_lg` or
  `coordinator` (decision 0028; the import contract "Workflows depend on no agent runtime"): an
  agent step's runner comes in through `StepContext.run_agent`.
- Saving is the consent: a site or folder outside what `permissions.granted_by` lists stops a run.
- An agent step's runner keeps one agent per `AgentRequest.key` and never redoes finished work;
  an answer counts only for the call it names (`call_id`), since a resume replays earlier answers.
- An agent step that reads outside content may only make READ calls, unless `trusted_input`.
- A bounded step's allowlist, declared folders and sites are its consent: a call beyond them
  waits for a person (`agent_step.decide`, `permissions.outside_declared`), never runs unasked.
- A test run stops before an approval step, an ask step without defaults (it doesn't wait at a wait step) and before a step marked `irreversible` (unless
  `send_for_real`, refused when no one is watching; decision 0029), and writes no run history.
  A revision (`revise_workflow`) keeps every step the workflow it revises marks `irreversible`.
- Healing (decision 0030) acts only for a browser tool step, only at `self_healing` or above,
  with the page tools on the sites `granted_by` lists, and on a step marked `irreversible` every
  call that does more than read waits for a person. To reach its step it may fill a field the
  page now requires, correct a value the page refuses, and press the form's own Next, Continue
  or Review (decision 0030, the maintainer's choice on 2026-11-01). `heal_guard` refuses any
  value typed or picked that isn't in the loop's current item or the step's own arguments. It
  sends what another `irreversible` step sends only to resend one that ran earlier in the same
  pass, and then every change waits for a person. What it did is on the step's record
  (`agent.healed`) and in the run report. A heal changes the saved workflow only when the person
  saves its fixes (`heal_fixes`), and a fix replaces an argument only while it still holds the
  value the heal replaced.
- Decision 0032: a step marked `irreversible` is never tried again on its own (the spec refuses retries on it); a failure that doesn't stop the run is on the step's record (`recovered`) and in the run report, never counted as done; the steps after a failed run never wait for a person, and their failure never replaces the run's own error. Decision 0033: a run paused at an ask or wait step holds nothing but its checkpoint; only `WorkflowRun.answer` or `wake` continues it, and a wait looks only whether its file is there. Decision 0035: a called task runs on its own checkpoint thread under its own approval mode, at most `MAX_TASK_DEPTH` deep and never in a cycle; its pauses pass up keyed by where it stopped, and a test run guards its steps as its own. Decision 0036: each lane of a parallel step runs on its own checkpoint thread from the caller's values; its pauses pass up one at a time, a retry goes on only in the lanes that failed, and lanes that may use the browser take turns.
- Decision 0042: steps are added only at `proactive` or above, only where `StepContext.adds_steps` is on (never in a called task, a lane, `after_failure` or the added steps), and never for a person's no, a permission or an irreversible step. A plan holds only tool, llm and check steps, is checked as the step's `on_failure: steps` and against `_new_literals` on every pass, and an approval goes in front of each tool not in `StepContext.read_tools`. The plan is kept in the run's state: a resume never plans or tries the step again.
- `UNAVAILABLE_TOOLS` in `preflight.py` only lists tools a run may not call; the import contract,
  not that list, is what keeps the code module out.

## Tests
`tests/test_workflow_spec.py`, `tests/test_workflow_engine.py`, `tests/test_workflow_agent_step.py`, `tests/test_workflow_permissions.py`,
`tests/test_workflow_catalog.py`, `tests/test_workflow_solidify.py`, `tests/test_workflow_testing.py`, `tests/test_workflow_healing.py`, `tests/test_workflow_report.py`, `tests/test_workflow_failures.py`, `tests/test_workflow_pauses.py`, `tests/test_workflow_run_task.py`, `tests/test_workflow_parallel.py`, `tests/test_workflow_overview.py`, `tests/test_workflow_added_steps.py`; `tests/web/test_scheduled.py` and `tests/web/test_scheduled_parallel.py` cover runs through the server.

## Verify by hand
Drafting a workflow from a real conversation with a real model (`solidify`); a browser step on a real Windows machine; added steps (0042) planned by a real model.

## Reviewed
2026-10-12 (pilot card; the sha is added when the card is first checked against a later change).
