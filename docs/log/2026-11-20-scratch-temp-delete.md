# Scripts' temp files stop landing in the workspace (shipped)

Why: people found batches of 4-byte `blat` files with 8-character names in their workspace
(issue #974). Windows replaces a contained run's TEMP and TMP with the container's own
`AC\Temp`, which the folder guard refuses, so Python's `tempfile` fell through to the working
directory, the workspace. There it could write its probe files but not delete them, and left
100 per run.

## Shipped
- The Python wrapper (`tools/exec/script_guard.py`) pins `tempfile.tempdir`, TEMP and TMP to the
  run's scratch folder, from `COSCRIBE_SCRATCH_TEMP`, which `isolation.start` copies from the TEMP
  it was given, so the probe never runs.
- `script-scratch`, coscribe's own folder for a run's files, is granted `RX,W,D` under a new
  `scratch` capability (`tools/exec/isolation.py`), so temp files there can be deleted. The
  person's folders keep `RX,W` without DELETE. Decision
  [0056](../decisions/0056-a-scripts-own-scratch-folder-allows-delete.md) narrows 0021.
- Tests: the grant's rights and the run's capabilities (`tests/test_isolation.py`), the pin with
  a probe that can't be deleted (`tests/test_script_guard.py`), and two container tests for the
  Windows CI job: `NamedTemporaryFile` and `TemporaryDirectory` in the scratch folder of a real
  container, and a `run_python_script` that uses temp files leaving the workspace empty.

## Not verified
- A real Windows machine by hand; the container tests run in the Windows CI job.
- The files earlier runs left in workspaces are not removed.

## Follow-ups
- Node and native code in a contained run still get the container's `AC\Temp`, which Node's
  permission flags don't allow; nothing is left in the workspace, but such a write fails.
