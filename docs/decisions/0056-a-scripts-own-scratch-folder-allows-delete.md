# 0056: A script's own scratch folder allows delete

Status: proposed (2026-11-20, issue #974). Narrows 0021: the rule that a read-write grant has no
DELETE now covers the person's folders only, not coscribe's own `script-scratch`.

## Context
An isolated script's `TEMP` and `TMP` point at its folder under `script-scratch` (the system
temp folder is out of the container's reach). That folder was granted like the person's folders,
`RX,W` without DELETE. Python's `tempfile` trusts a temp folder only after it writes a probe file
(`blat`, 4 bytes, an 8-character name) and deletes it. In the container the delete failed, so
`tempfile` tried 100 names, moved on to the next candidate and ended at the working directory,
the workspace, where it left 100 more. People found batches of these files in their workspace.
`NamedTemporaryFile` and `TemporaryDirectory` also need DELETE on Windows, so they failed too.

## Decision
- `script-scratch` is granted to its own capability with `RX,W,D` (`scratch` in
  `tools/exec/isolation.py`). Every run holds it, as it held the write grant before.
- The person's folders keep `RX,W` without DELETE: a script still can't remove or rename their
  files, and deletes still go through a trusted tool.
- The Python wrapper sets `tempfile.tempdir` to the scratch folder when `TEMP` points there, so
  the probe never runs and a failed grant can't send temp files into the workspace.

## Consequences
- A script can delete files in any run's scratch folder, another conversation's included. It
  could already overwrite them, and they hold only the script text, its guard config and temp
  files, which coscribe removes when the run ends.
- The old `write` ACE on `script-scratch` stays until the folder is swept; it is harmless.
- Files that earlier runs left in a workspace are not removed: they can't be told apart from
  the person's own files with certainty.
- Not verified on a real Windows machine; the container test runs in the Windows CI job.
