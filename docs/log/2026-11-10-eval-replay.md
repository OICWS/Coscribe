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
- Four tapes, recorded on `deepseek:deepseek-flash` at low effort: tasks 02 (24 files read one by
  one, through compaction), 04 (a research sub-agent), 05 (a preference remembered) and 10
  (twelve files read through compaction). All recording, the discarded tapes included, cost
  about $0.42.
- `tests/test_evals_agentic_replay.py` replays them in the PR checks, under a second each, and
  asserts no tool error, every answer used, each turn calling the tools it called when recorded,
  the task's own checks passing and no model called.

## Found on the way
- Task 01's tape replayed the same on Python 3.13 and differently on 3.11 (CI). The model makes
  eight `task_create` calls in one answer; they run in threads, so which call gets which id
  follows thread scheduling, and the recorded answers then update the wrong tasks. In the app
  this shows as a plan in another order than the model wrote it. `TaskToolkit.create` also reads
  and raises `_next_id` with no lock. Not fixed here (`docs/plan.md`); task 01 has no tape
  until it is.
- Task 07's tape took 15 s and called tools in another order on 3.11, so it is not kept either.

## Not verified
- Windows: the tapes were recorded on Linux. Paths are stored as `{{WORKSPACE}}` and `{{ROOT}}`
  and written back in the replaying machine's spelling; CI's Windows job is the first real run.
- That a tape outlives ordinary change: it held across the three merges of `main` made while this
  was written, no longer history than that.

## Follow-ups
- Tasks 03, 08 and 11 run a script and so need an interpreter the replaying machine may lack; no tape
  until the script tool can be answered from the tape too.
- A tape is tied to the tool list: a new tool does not break it, a renamed one does. If tapes
  need recording more than about once a month, record them in a scheduled job instead of by hand.
