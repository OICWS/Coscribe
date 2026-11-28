# evals: read before you run one

An eval that calls a model spends the maintainer's money: an OfficeVal pass over every task cost
about $8. How to run each eval is in `README.md`. This file covers how to keep the bill down.

## Ask first

- Estimate a run's cost before starting it, from the cost per task of the last comparable run in
  `evals/runs/*/summary.json`. Under $1, run it and report the result. At $1 or more, or for a
  full pass over a benchmark, ask the maintainer first: say which tasks, how many, and the
  expected cost.
- Use the model and effort of the baseline you compare against (`deepseek-flash`). Never switch
  to a larger model to "see if it helps": that is a different experiment and needs its own ask.

## Rerun only what a change can reach

- A fix is checked on the dev tasks it can reach (`README.md`, "Development and held-out tasks"),
  rerun on their own and compared with those tasks' rows in the baseline run. A full pass over a
  benchmark happens only on a frozen implementation, at the end, and only when asked for.
- Free first: where an eval has `--check-only`, re-check a saved run with no model calls. A change
  to a conversation's handling is tested with `agentic/replay.py`, which replays the recorded
  answers with no model. Pay for a model run only for what needs new model output.
- Leave the model and the prompt alone unless the change is about them. Each such change makes
  earlier baselines stale, so they have to be paid for again.

## Where the money goes

On the OfficeVal runs (#1078), a task took about 60 model calls, and each call resent the whole
conversation (about 100k tokens). Splitting the bill of 20 dev task runs by token type:

| Part | Share | Note |
|---|---:|---|
| Model output | 49% | about two thirds of it reasoning |
| Input missing the cache | 22% | |
| Resent context hitting the cache | 29% | about 50 times cheaper per token than a miss |

- Compare cost per task and model calls per task, not only the score, when two runs are compared.
  `summary.json` has both.
- Run off-peak. The provider's discount hours are noted in `prices.py`; check the vendor's
  pricing page again before relying on them.

## Tried and rejected

Don't retry these without a new reason.

- **Prompting the agent to check once and in full, plus a zoom `region` for `look_at_image`**
  (#1112, closed). On the same 10 dev tasks, score went from 0.382 to 0.384, cost from $0.84 to
  $0.87 and calls from 772 to 796. The model never used the region. Single tasks swung by up to
  0.7 between runs, so one run of 10 tasks can't detect a change this small.
- **Trimming old tool results from the context** (analysed, not built):
  - It can only reach the 29% cached share above.
  - The provider caches a prompt by its unchanged beginning. Cutting anything earlier turns the
    rest into cache misses, which cost about 50 times more.
  - A result the agent needs again costs a new call to read it back.
- **What would move the bill** is output, mostly reasoning: a lower reasoning effort. That
  changes the model's behaviour, so it is an experiment the maintainer approves first. It is
  measured on dev tasks against the score.
