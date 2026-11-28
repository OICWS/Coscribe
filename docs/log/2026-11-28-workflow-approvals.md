# A scheduled task's tiers use Auto mode's reviewer and Bypass mode (shipped)

Why: a task saved as "Automatically approve" still parked every script, command and connector
call for a person who is not there, so most runs ended as `needs_approval`; and "Never ask"
approved everything with no switch to hold it back (#1106 block 3, the design agreed with
Collins; decision 0062).

## Shipped
- `tools/bookkeeping/scheduled_tasks.py` `ScheduledTrigger.tier`: "skip" holds only while Settings ›
  General's "Allow bypass permissions mode" is on; otherwise the task runs as "auto". A prompt
  run, a workflow run, a called task and a person finishing a parked run all take their tier
  through it.
- `conversation/approvals.py`: in a run whose tier is "auto", a call the tier doesn't approve on
  its own (code, a connector, a command 0022 keeps from the person) goes to Auto mode's
  reviewer, with the run's prompt as the person's request. A run's "skip" approves where Bypass
  mode does, under the same floor (hooks, forbidden exec rules, workspace deny and ask rules, a
  switched-off capability).
- `workflows/agent_step.py` `AgentRequest.review_as` and `runtime_lg/workflow_agent.py`: a high
  or full agent step of an "auto" task asks the reviewer before it parks, weighed against the
  step's title and goal as saved (not rendered with what earlier steps brought in). Allowed
  calls are audited as `auto_review`, blocked ones refused to the agent as `auto_review_block`;
  no verdict parks the run as before. A bounded step, an approval or ask step and a heal's guard
  are unchanged.
- The task editor, the task page, the scheduled-task tool's docstring, the README and the site's
  page say what each tier does now.

## Not verified
- A real scheduled run on Windows with a real reviewer model: the tests use a scripted reviewer.

## Follow-ups
- A prompt run whose reviewer gives no answer refuses the call instead of parking it: parking
  would need the decision made before the run decides the interrupt (`docs/plan.md`).
