# A run's token budget counts what its llm steps use (shipped)

Why: a run asks before its models use more tokens than its task's runs did (decision 0043, #843),
but only agent steps' tokens were counted. A loop of llm steps over many items spent on without
the run ever asking, and the run page's token total left them out.

## Shipped
- `workflows/model_step.py`: `ask_model` takes an optional `usage` and adds to it what each reply
  reports, the forced tool call (read with `include_raw`, so its reply's usage is kept) and the
  bare-JSON fallback alike. A forced call that doesn't parse still falls back, as before.
- `workflows/step_work.py`: `run_llm` returns its fields and `{"tokens", "cached_tokens"}`, the
  shape an agent step's activity has. They go on the step's record (`agent`), so the run budget
  (`budget.py`'s `tokens_of`) and the run report count them with no change there. Cache reads are
  left out of the budget, as for an agent step.
- Decision 0043 says llm steps are counted.
- Tests: `tests/test_workflow_token_budget.py` (an llm step's tokens on its record, cache reads
  apart; both calls counted when the forced call doesn't parse; a run of llm steps past its cap
  asks before the next one and goes on when told).

## Not verified
- Real providers' usage numbers on the structured-output route; the test model reports them on
  the reply as LangChain's chat models do.

## Follow-ups
- An llm step that fails after its one retry keeps no record of the tokens it used.
