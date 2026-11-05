# A multi-turn evaluation of how far a conversation gets on its own (shipped)

Why: the agentic steps of #819 (a plan check, a side-call model, a delivery check, a folder brief) each need a number from before and after them. The office evaluation sends one message and looks at a file. It doesn't show a conversation that stops with work left, repeats a call, leaks a compaction summary or needs a person to push it.

## Shipped
- `office-agent/evals/agentic/`: eleven tasks.
  - Two use plans and long reads, run through compaction.
  - One prints large script output.
  - One delegates to a sub-agent.
  - One asks coscribe to remember a preference.
  - One asks for two deliverables.
  - One has a correction in the second turn.
  - One asks for something that isn't there.
  - One asks for five files at once.
  - One works through twelve files with a plan, run through compaction.
  - One names a file slightly wrong.
- The scripted user approves, saves `remember` offers and answers every other question with "decide it yourself". A failed check gets one generic nudge, and the checks run again.
- Metrics per task and for the run: whether the task was done (and done after the nudge), open tasks, repeated identical calls, summary leaks, questions, approvals, cost and time.
- `tests/test_evals_agentic.py` covers the inputs, checks, scripted user and metrics without a model.
- README section in `office-agent/evals/README.md`.

## Baseline on `main` (c95ff29, `deepseek:deepseek-flash`, effort low, one run)
- 11/11 done without help, so no task needed the nudge.
- 0 open tasks at the end and 0 summary leaks.
- 4 repeated calls (3 of them in the five-file task).
- 1 question (the remember offer), 0 approvals.
- 120 tool calls.
- $0.20 and 14 minutes of task time.

## Not verified
- Only run with `deepseek:deepseek-flash`, once per task. This model finishes every task here, so the set can't yet show a gain from a change that helps a turn finish. A weaker model or harder tasks would.

## Follow-ups
- Steps 2 to 6 of #819, each scored by this evaluation (`docs/plan.md` item 9).
