# A multi-turn evaluation of how far a conversation gets on its own (shipped)

Why: the agentic steps of #819 (a plan check, a side-call model, a delivery check, a folder brief) each need a number from before and after them. The office evaluation sends one message and looks at a file. It doesn't show a conversation that stops with work left, repeats a call, leaks a compaction summary or needs a person to push it.

## Shipped
- `office-agent/evals/agentic/`: eight tasks.
  - Two use plans and long reads, run through compaction.
  - One prints large script output.
  - One delegates to a sub-agent.
  - One asks coscribe to remember a preference.
  - One asks for two deliverables.
  - One has a correction in the second turn.
  - One asks for something that isn't there.
- The scripted user approves, saves `remember` offers and answers every other question with "decide it yourself". A failed check gets one generic nudge, and the checks run again.
- Metrics per task and for the run: whether the task was done (and done after the nudge), open tasks, repeated identical calls, summary leaks, questions, approvals, cost and time.
- `tests/test_evals_agentic.py` covers the inputs, checks, scripted user and metrics without a model.
- README section in `office-agent/evals/README.md`.

## Not verified
- Only run with `deepseek:deepseek-flash`. The baseline numbers on `main` are in the PR.

## Follow-ups
- Steps 2 to 6 of #819, each scored by this evaluation (`docs/plan.md` item 9).
