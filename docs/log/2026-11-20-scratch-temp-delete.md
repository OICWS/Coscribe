# Scripts' temp files stop landing in the workspace (shipped)

Why: people found batches of 4-byte `blat` files with 8-character names in their workspace
(issue #974). In the container a script's TEMP folder had no DELETE, so Python's `tempfile`
couldn't remove its probe file, gave up on TEMP after 100 tries and probed the working
directory, the workspace, leaving 100 more.

## Shipped
- `script-scratch`, coscribe's own folder for a run's files and TEMP, is granted `RX,W,D` under
  a new `scratch` capability (`tools/exec/isolation.py`). The person's folders keep `RX,W`
  without DELETE. Decision [0056](../decisions/0056-a-scripts-own-scratch-folder-allows-delete.md)
  narrows 0021.
- The Python wrapper (`tools/exec/script_guard.py`) pins `tempfile.tempdir` to the scratch folder
  when TEMP points there, so the probe never runs.
- Tests: the grant's rights and the run's capabilities (`tests/test_isolation.py`), the pin with
  a probe that can't be deleted (`tests/test_script_guard.py`), and two container tests for the
  Windows CI job: `NamedTemporaryFile` and `TemporaryDirectory` in a real container, and a
  `run_python_script` leaving the workspace empty.

## Not verified
- A real Windows machine: the container tests run only in the Windows CI job.
- The files earlier runs left in workspaces are not removed.
