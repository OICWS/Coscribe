# The app shows, edits and runs a workflow's agent step (P2a of #719; shipped)

Why: since #727 and #730 a workflow can hold an agent step (decision 0028), but the frontend
knew only the seven step kinds before it, so such a workflow's page, editor and run view had no
way to show what the step is, what saving it allows, or the call it is waiting on.

## Shipped
- `types/workflow.ts`: `AgentStep`, `Autonomy`, and a workflow `version` of 1 or 2. The step has
  its own colour (`--kind-agent`, light and dark), a target icon (`parts.tsx`), a line on the
  step card (`StepSummary`: how many tools or how broad, the fields, where the result goes) and
  an entry in the add-step menu.
- `AgentEditor.tsx`: the goal, how far it goes on its own ("Within limits", "Broad", "Whole
  task" for 0028's bounded, high and full), the tools of a bounded step, the folders and sites
  it may use, its fields (none means its result is its report), whether it may act on what it
  reads from outside (`trusted_input`), its step cap, model and result name. Switching level
  drops what the server refuses at that level (a tool list above bounded, fields on a whole-task
  step). Saving a step of this kind makes the workflow version 2 (`workflowEdit.versionFor`).
  The fields table and the shared editor parts moved to `editorParts.tsx` so the two editors
  share them.
- `WorkflowPermissions.tsx`: an "Agent steps" row lists each one with its level, its tools or
  that it has all of them under the task's approval setting, its folders and sites, its step
  cap, and when it may only read because what it is given comes from outside (the server's
  `agents` list, which this reads for the first time).
- Run view: a waiting agent step shows the one call it wants (the tool and its arguments) in
  `WaitingCard.tsx` (the approval card, moved out of `WorkflowRunView.tsx`), says the answer
  covers that call only, and that a note goes to the agent when the call is declined. A running
  step says "Working on it…"; a finished one shows how many tool calls it made, an "Agent" tag,
  and under its output the tools it called and the tokens it used (`AgentActivity.tsx`).
- `workflowTree.scopes` lets later steps pick an agent step's fields, or `<name>.report`;
  renaming a value renames it in a goal; a failed check offers to retry from the agent step
  whose result it read; the task's badge counts agent steps as using a model.
- Tests: `lib/workflowAgentStep.test.ts` (scopes, renames, new step, check source) and
  `tests/e2e/workflow-agent.spec.ts` (the page and permissions card for a version 2 workflow;
  an agent step added in the editor saves and makes the workflow version 2).

## Measured
- With #734's runner, on its branch before it merged, on `deepseek:deepseek-flash`: a broad
  step paused on `write_file`, the card showed the call's path and content, declining let the
  agent finish, and the row showed "2 tool calls" with the report. The step used about 104k
  tokens in all: the whole tool list goes with each call (cached by the provider), which a cost
  cap would count.

## Not verified
- On Windows, and in the desktop app (checked in Chromium against `coscribe-web`).
- The live run, again on `main` after #734 merged.

## Follow-ups
- P2b: the read-only canvas of a workflow.
