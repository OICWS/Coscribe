# A run may add steps when a step fails, at proactive or above (shipped)

Why: #843 batch 3. At `proactive` or `autonomous` the person already lets agents decide how a step
is done, yet a step that failed in a way its `on_failure` and healing didn't cover still stopped
the run. Decision 0042; the maintainer chose to add steps only when a failure isn't recovered.

## Shipped
- **Planning** (`workflows/added_steps.py`). When a tool, script, model or agent step would stop
  the run, a model plans at most 5 tool, llm or check steps for what it was for. The plan is
  checked as that step's `on_failure: steps` (scope, the task's ceiling, tools that exist here).
  A literal argument must be in the saved workflow or the loop's item, checked again on every
  pass. Scripts, agents, asks, waits and run-task steps are refused. The error and values are
  marked as data in the prompt. A refused plan stops the run with the step's own error and why.
- **Consent.** An approval step goes in front of every added tool step whose tool isn't in
  `StepContext.read_tools` (a connector's tool never is), so the run waits for a person even
  unattended. A test run stops there.
- **Running.** The plan is kept in the run's state (`added`) and runs as a called task does, on
  its own checkpoint thread, its records `<step>/added/<id>`, its pauses passed up. A resume never
  plans or tries the step again. A later pass of the step in a loop uses the same plan.
- **Where it doesn't apply:** below `proactive`, a person's no, a folder or site the run may not
  use, an irreversible step, a called task, a parallel lane, `after_failure` and the added steps
  themselves (`StepContext.adds_steps` is off there; only a conversation's run context turns it
  on).
- **The report** lists "Steps the run added" with why. "Save into the task" keeps them as the
  step's `on_failure: steps` (`added_fix`, in the run report's `added_fix`). The failed step's
  record is `recovered: "added"`, with the plan and the planner's tokens.
- The routing helpers moved out of `engine.py` into `routing.py` to keep it under the size limit;
  `solidify.py` takes `UNAVAILABLE_TOOLS` from `preflight.py` to avoid an import cycle.

## Checked
- `tests/test_workflow_added_steps.py`: added steps stand in for the failed one; below
  proactive nothing is planned; a writing step waits for a person and the plan is made once; a
  value from outside and a script are refused; a loop reuses the plan and refuses one item's value
  on the next; the report and the revision.
- Screenshots against the stub backend, with a planner reply scripted for them: the approval in
  front of an added step and the report section.

## Not verified
- A plan from a real model. A real failure on a real Windows machine.
