# A contained script can open its own scratch folder on Python 3.13+ (shipped)

Why: on a Windows machine running Python 3.13 or later, every contained `run_python_script`,
`run_node_script` and background script failed with "Permission denied" before its first line.
Each run's folder under `script-scratch` was made with `tempfile.mkdtemp`, whose mode 0o700 gives
the folder an owner-only ACL from 3.13 on; that drops the AppContainer grant the folder would
inherit from `script-scratch`, so the container could not open its own `script.py` or guard
wrapper. CI runs 3.11, where `mkdtemp` sets no ACL, so nothing caught it.

## Shipped
- `tools/exec/isolation.py`: `new_scratch_dir(state_dir, prefix)` makes the run's folder under
  `scratch_root` with a plain `mkdir`, so it inherits the grant. The three script paths
  (`scripts.py`, `node_scripts.py`, `bookkeeping/background_tasks.py`) use it; `script_scratch_root`
  leaves the `tools.exec` interface in its place.
- `tests/test_isolation.py`: a run folder is new each time and skips a taken name (everywhere);
  on Windows, a run folder carries the scratch grant's capability SID.

## Not verified
- CI's Windows jobs run Python 3.11, so the Windows test there passes with or without the fix;
  the failure and the fix were seen on a Windows 11 machine with Python 3.14.

## Follow-ups
- A Windows CI job on Python 3.13+ would catch this class of change (in `docs/plan.md`).
