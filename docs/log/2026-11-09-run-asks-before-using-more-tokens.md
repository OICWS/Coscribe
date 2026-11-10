# A run asks before its models use more tokens, with nothing to set (shipped)

Why: #843, the cost cap the plan listed for an agent step. An agent step was capped only in model
calls and a run not at all, so a loop or an agent going in circles spent on with no one there.
Decision 0043; the maintainer asked that the person set nothing and that going over pause the run,
not fail it.

## Shipped
- **An agent step** (and an agent healing a step) asks after 300k new tokens per pass
  (`workflows/budget.py`'s `STEP_TOKENS`). `runtime_lg/token_limit.py` stops the agent before
  its next model call, counted from its history, so a pause for an approval doesn't reset it.
  Cache reads are left out: they are billed far lower and a long agent re-reads them every call.
- **A run** asks before an agent or llm step once it has used 3 times what its task's finished
  runs used at most, and at least 2M (`run_budget`, from the stored step records, so a resumed
  run counts what it spent before). `runtime_lg/scheduled_tasks.py` builds it per action.
- **Over it, the run waits** with a card: "The agent has used 340k tokens and isn't done yet",
  Continue or Stop. Continue lets it use as many again and the agent picks up where it stopped (a
  run's raised cap is kept on the run as `token_cap`); Stop ends the step as a person's no. The
  answers carry call ids, so a resume never takes one pause's answer for another's.
- **No setting**: nothing in the spec, the save card or the drafter's prompt.
- **Tool results with their own arguments**: calls made together could finish out of order, and
  each result took the arguments of the oldest call with its name, so two parallel `read_file`
  rows could show each other's paths. They are now matched by call id
  (`conversation/turn_stream.py`).

## Checked
- `tests/test_workflow_token_budget.py`: an agent past its share asks and goes on where it
  stopped; Stop is a person's no; an answer is never taken for another pause in the same step,
  either order; a run past its cap asks before its next model step and keeps the raised cap; the
  cap follows the task's runs and leaves cache reads out. `tests/test_tool_result_args.py`.
- Screenshots against a stub model that reports 170k tokens a call.

## Not verified
- A real model's usage numbers across providers (only OpenAI-shaped usage from the stub).
- On Windows and in the desktop app.
- LLM steps' tokens are not counted yet.
