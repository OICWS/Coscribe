# 0043: A run asks before its models use more tokens, with no setting

Status: proposed (2026-11-09, OICWS; the maintainer chose "no setting for the person" and a
pause, not a failure). Fills in the cost cap 0028 gave agent steps. Part of #843.

## Context
An agent step was capped only in model calls (`max_steps`), and a run not at all: a loop over
many items, or an agent going round in circles, spent on with no one there. A bounded agent step
used 70k to 107k tokens to write one short file (`docs/log/2026-10-31-workflow-run-canvas.md`).
The maintainer wants the person to set nothing.

## Decision
- **The unit is new tokens**, as the provider reports them, less what it served from its cache
  (billed far lower, and re-read on every call of a long agent). No price table: prices change and
  a local model costs nothing. The number is the one the run page already shows.
- **An agent step** (and an agent healing a step) may use `STEP_TOKENS` (300k) per pass before it
  asks; the runner stops it before its next model call (`runtime_lg/token_limit.py`).
- **A run** may use what its task's finished runs used at most, times 3, and at least 2M
  (`run_budget`), counted from its step records, so a resumed run counts what it spent before.
  It is checked before each agent or llm step. A single llm call isn't counted.
- **Over it, the run pauses**, as for an approval: "Continue" lets it use as many again (the
  agent goes on where it stopped; a run's raised cap is kept on the run, `token_cap`), "Stop"
  ends the step as a person's no, so its `on_failure` applies and nothing heals or adds steps.
  Unattended steps (`after_failure`) are not asked: they fail.
- **Nothing to set.** No field in the spec, nothing on the save card; the drafter isn't told.
- Answers are matched by call id (`tokens-<scope>-<used>`), so a resume never takes one pause's
  answer for another's.

## Consequences
- `AgentRequest` gains `max_tokens` and `go_on`; `AgentReply.status` gains `"over_budget"`;
  `StepRecord` gains `over_budget`; `StepContext` gains `budget`; `ScheduledRun` gains
  `token_cap`.
- A test run stops at the question as at an approval.
- Not done: counting llm steps, and a cap for a prompt task (a task that is one instruction).
