# evals: read before you run one

An eval that calls a model spends the maintainer's money: an OfficeVal pass over every task cost
about $8. How to run each eval is in `README.md`. This file covers how to keep the bill down.

## Ask first

- Ask the maintainer before any run that is more than a handful of tasks. Say which tasks, how
  many, and the expected cost. Use the cost per task of the last comparable run in
  `evals/runs/*/summary.json`.
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
conversation (about 100k tokens). Caching made the resent input cheap; about half the bill was
the model's own output. Most calls were small scripts that each checked or zoomed in on one
thing. To lower the cost:

- Cut the number of calls per task rather than tokens per call. A change that makes the agent
  check once and in full, or see something directly (`look_at_image` with a region) instead of
  measuring it in a script, saves a whole conversation resend for every call it removes.
- Compare cost per task and model calls per task, not only the score, when two runs are compared.
  `summary.json` has both.
- Run off-peak. The provider's discount hours are noted in `prices.py`; check the vendor's
  pricing page again before relying on them.
