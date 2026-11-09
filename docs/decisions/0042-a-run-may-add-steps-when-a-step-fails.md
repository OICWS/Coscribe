# 0042: A run may add steps when a step fails, at proactive or above

Status: proposed (2026-11-09, OICWS; the maintainer chose "only when a failure isn't recovered").
Narrows 0028 (the steps a run follows may grow) and 0032 (a failure may run added steps).
Part of #843.

## Context
A step that failed in a way its `on_failure` and healing didn't cover stopped the run, even at
`proactive` or `autonomous`, where the person already lets agents decide how a step is done. An
export moved behind a new page, or a file that is now .xls, needs a step or two the task lacks.

## Decision
- **When:** the task is `proactive` or `autonomous` (0030), and a tool, script, model or agent step
  still fails after its tries, `on_failure` and healing, and would stop the run. Not for a
  person's no, a skipped loop item, `after_failure`, a step marked irreversible, a step in a
  called task, or a step the added steps themselves run.
- **The plan** (a model call in `workflows`, as drafting is) is at most 5 tool, model or check
  steps, without retries or `on_failure`. It is checked as the failed step's `then: steps`
  would be (0032's scope: its last step saves the failed step's name). Tools must exist here;
  no script, agent, ask, wait or run-task step. A literal argument must come from the saved
  workflow or the loop's item: an address read from a page never becomes a recipient. The
  planner reads the error and values as data, never as instructions. A refused plan stops the
  run with the original error and why.
- **Consent:** an approval step goes in front of every added tool step whose tool isn't READ
  (risks come through `StepContext`; a connector's tool never counts as READ), so the run
  waits for a person even unattended, and a test run stops there. Sites and folders outside
  what the task may use pause through `NeedsPermission`, as any step's do.
- **Running:** the plan is kept in the run's state; the step's node runs it on its own
  checkpoint thread, as a called task (0035), and on resume goes on there: it never plans or
  tries the step again. Its records are `<step>/added/<id>`. A later pass of the step in the
  same run uses the same plan.
- **Nothing silent:** the failed step's record is `failed` with `recovered: "added"`, the
  plan and the planner's cost; the report counts it as not done and lists the added steps.
  The run offers them afterwards as that step's `on_failure: steps`, which the person saves.

## Consequences
- `StepContext` gains the READ tools; `StepRecord.recovered` gains `"added"`.
- Out of scope: adding steps when nothing failed (a case no branch handles).
