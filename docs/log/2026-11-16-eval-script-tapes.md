# The agentic tasks that run a script replay from their tapes too (shipped)

Why: three of the agentic evaluation tasks (03, 08, 11) run a Python script, so they had no tape:
a replay would need the interpreter, the script environment and the network that the recording
machine had (`docs/log/2026-11-10-eval-replay.md`, follow-up). Part of #867.

## Shipped
- `evals/agentic/replay.py`: a tape also holds what each Python or Node script printed, its exit
  code and whether it timed out, taken where the script tools start the interpreter
  (`run_to_end`). On replay that output stands in for the interpreter, and the script
  environment, the Node environment and the isolation are not set up. What the tools do with
  the output still runs: task 03's 20,000 printed rows are cut and kept whole, and the model's
  `search_files` over the kept file works as it did when recorded.
- Tapes for 03 (one script, 406k characters of output: the tape is 429 KB), 08 (six scripts) and
  11 (one script), recorded on `deepseek:deepseek-flash` at low effort for $0.026. Eight tasks
  replay now, about 6 s for all; each replays the same on Python 3.11 and 3.13, five runs in a
  row.
- `tests/test_evals_agentic_replay.py`: a replay starts no process (fails if the interpreter is
  started), and a tape one script short fails with "record again".

## Not verified
- Windows: a script's output may name paths; they are stored as `{{WORKSPACE}}` and `{{ROOT}}`
  like the rest of a tape. CI's Windows job is the first replay there.

## Follow-ups
- A script's files are not written on replay; a task whose later turn reads what a script wrote
  cannot be taped this way. None of the three does.
- `run_background_script` and `run_background_command` are not on the tape.
- A nightly replay of the three tasks that write Office files (`docs/plan.md`).
