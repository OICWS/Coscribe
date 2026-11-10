# Agentic evaluation tasks replayed from recorded answers in the PR checks (partly shipped)

Why: the agentic evaluation needs a real model, so it runs by hand and no pull request is held to
it. A change to the loop, the middleware or a tool could break a whole conversation and only the
next paid run would show it. Issue #867; row 4 of the engineering assessment of 2026-11-09.

## Shipped
- `evals/agentic/replay.py`: a tape holds every answer a model gave in one task's run (agent,
  sub-agent and side calls), its token counts, the provider, the context window and each turn's
  tool names. `TapeModel` answers from it; the loop, middleware, approvals and tools run for real.
- `python -m evals.agentic.run --record DIR` writes tapes, `--replay` runs from them
  (`evals/README.md`).
- Two tapes, recorded on `deepseek:deepseek-flash` at low effort: task 01 (a plan of eight
  reports, 102 KB) and task 10 (twelve files read through compaction, 36 KB). Recording both cost
  about $0.33.
- `tests/test_evals_agentic_replay.py` replays both in the PR checks, about a second each, and
  asserts no tool error, every answer used, each turn calling the tools it called when recorded,
  the task's own checks passing and no model called.

## Not verified
- Windows: the tapes were recorded on Linux. Paths are stored as `{{WORKSPACE}}` and `{{ROOT}}`
  and written back in the replaying machine's spelling; CI's Windows job is the first real run.
- That a tape outlives ordinary change: it held across the three merges of `main` made while this
  was written, no longer history than that.

## Follow-ups
- Tasks 08 and 11 run a script and so need an interpreter the replaying machine may lack; no tape
  until the script tool can be answered from the tape too.
- A tape is tied to the tool list: a new tool does not break it, a renamed one does. If tapes
  need recording more than about once a month, record them in a scheduled job instead of by hand.
