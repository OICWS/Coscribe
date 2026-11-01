# A drafted data workflow stops instead of guessing when its input changed (shipped)

Why: the data eval (#768) found drafted workflows that finished with a wrong report when the
file of a run was not as in the conversation (a renamed column, another encoding, a reference
written differently): 4 false successes and 1 guess in 39 drafted runs.

## Shipped
- `workflows/solidify.py`:
  - The drafter is told that a script reading a file of the run checks the columns it uses,
    raises on a blank value a result needs and on a row it can't place (incoming money that
    names no record it can find included), matches an id however it is written, and decodes
    strictly.
  - It is told that a `run_node_script` step holds `stdout`, `stderr` and `exit_code`, not what
    the script printed, and `check_draft` refuses a step that reads another field of one.
- `workflows/engine.py`: a script run as a tool step (`run_python_script`, `run_node_script`)
  that exits non-zero or times out fails its step; before, the step was done and the run went on.
- Eval (`evals/workflow/data_run.py --builds drafted --repeat 3`, DeepSeek flash): 42 runs,
  0 false successes and 0 guesses (from 4 and 1). pass@1 26% (from 33%): a run on a changed file
  now stops and its repair fixes it (REPAIRED) rather than passing by luck.

## Not verified
- The eval with another model than DeepSeek flash.

## Follow-ups
- The eval's first sales draft failed with "Resolve the pending approval first", the eval
  harness's conversation and not the draft; worth making the harness answer it.
