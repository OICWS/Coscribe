# The agentic tasks that run a script replay from their tapes too (shipped)

Why: three of the agentic evaluation tasks (03, 08, 11) run a Python script, so they had no tape:
a replay would need the interpreter, the script environment and the network that the recording
machine had (`docs/log/2026-11-10-eval-replay.md`, follow-up). Part of #867.

## Shipped
- `evals/agentic/replay.py`: a tape also holds what each Python or Node script printed, its exit
  code, whether it timed out and the files it created or changed in the workspace, taken where the
  script tools start the interpreter (`run_to_end`). On replay that output stands in for the
  interpreter and the files are written back; the script environment, the Node environment and
  the isolation are not set up. What the tools do with the output still runs: task 03's 20,000
  printed rows are cut and kept whole, and a later `search_files` over the kept file works.
  Output over 20,000 characters is stored gzipped, its folders marked first: task 03's tape is
  130 KB instead of 323 KB, under the repository's 200 KB limit for a text file.
- A sub-agent's and `review_work`'s reviewer's answers are on the tape now. Both run in a fresh
  context, which did not see the task's tape: recording dropped their answers, and on replay the
  sub-agent failed with "no tape" inside `spawn_agent`'s report, which the replay test did not
  see. Task 04's tape had replayed that way since it was made. A call outside its task's context
  now uses the one tape running (recording takes `--jobs 1`), and a replay's result counts the
  answers the tape could not give (`answers_missing`), which the test holds at 0.
- Tapes for 03, 08 and 11, and 04 again, recorded on `deepseek:deepseek-flash` at low effort.
  Eight tasks replay in about 7 s, the same on Python 3.11 and 3.13, five runs in a row.
  Recording, the discarded tapes included, cost about $0.20.
- Tasks 06, 07 and 09, which write Office files, also replay with these changes (09 in 30 s,
  with a script's CSV written back for the deck); they are for a nightly job, not this PR.

## Not verified
- One recording per task. The Windows CI job replayed all eight tapes (its only failure on the
  first push was the file-size check).

## Follow-ups
- `run_background_script` and `run_background_command` are not on the tape.
- A nightly replay of tasks 06, 07 and 09 (`docs/plan.md`).
