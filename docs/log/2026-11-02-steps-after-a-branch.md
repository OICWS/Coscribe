# Every step after a branch or a choice runs again (shipped)

Why: #777 wired the paths of a branch or a choice with a loop variable that took the name of the
list being wired, so the steps after the block were joined to the wrong list. A run that reached
the second step after a branch or a choice ended there and counted as completed, without running
the rest. Found by drawing the compiled graph of a workflow while designing batch 2 (#776).

## Shipped
- `workflows/engine.py`: the paths are wired under their own name, so the steps after a branch
  or a choice follow in order.
- `tests/test_workflow_paths.py`: a branch and a choice followed by three steps; all three run.

## Not verified
- Runs saved between #777 and this fix: one that reported completed may have skipped steps after a
  branch or a choice. Its step list shows which ran.
