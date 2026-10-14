# Reasoning effort, part 3: the evaluation runs at a level of the product's scale (shipped)

Why: once a conversation carries an effort level (#203), the evaluation setting `reasoning_effort` on
the model directly was overridden by the session's default (Medium), so a run meant to be at `low`
would have run at DeepSeek's `medium` and not been comparable with the baselines (#202).

## Shipped
- `evals/run.py --effort` takes the product's levels (low, medium, high, extra, max, ultra; default
  low) and hands the level to the session as its default, so each model runs it as the product
  would. `--effort none` is gone: the product does not offer it. `result.json` records the level
  and `effort_runs_as`, the level the model ran.
- Tests: the levels equal the product's; a session built for a run at `extra` sends DeepSeek
  `xhigh`.

## Not verified
- Nothing new on Windows.
