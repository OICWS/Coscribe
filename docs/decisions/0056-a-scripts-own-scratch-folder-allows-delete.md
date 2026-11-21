# 0056: A script's own scratch folder allows delete

Status: accepted (2026-11-21, by the maintainer; proposed 2026-11-20, issue #974). Narrows 0021: the rule that a read-write grant has no
DELETE now covers the person's folders only, not coscribe's own `script-scratch`.

## Context
People found batches of 4-byte `blat` files with 8-character names in their workspace. Python's
`tempfile` trusts a temp folder only after it writes such a probe file and deletes it. coscribe
set a contained run's TEMP and TMP to its folder under `script-scratch`, but Windows replaces both
in an AppContainer with the container's own `AC\Temp` (seen in the Windows CI job), which the
folder guard refuses. `tempfile` then tried the next candidates and ended at the working
directory, the workspace: there the guard allows the write, but the container has no DELETE, so
each of its 100 tries left a file behind. Pointed at `script-scratch` instead, `tempfile` would
fail the same way, since that folder had no DELETE either, and `NamedTemporaryFile` and
`TemporaryDirectory` need DELETE on Windows.

## Decision
- The Python wrapper sets `tempfile.tempdir`, TEMP and TMP to the run's scratch folder, read
  from `COSCRIBE_SCRATCH_TEMP`, which Windows leaves alone. The probe never runs.
- `script-scratch` is granted to its own capability with `RX,W,D` (`scratch` in
  `tools/exec/isolation.py`). Every run holds it, as it held the write grant before.
- The person's folders keep `RX,W` without DELETE: a script still can't remove or rename their
  files, and deletes still go through a trusted tool.

## Consequences
- Every run holds the same capability on the whole `script-scratch` tree, so any run can read,
  change and delete another run's script, wrapper and guard config, another conversation's
  included. Swapped before it starts, that code runs with the other run's folders and network,
  and a script can read another conversation's script text. Write access already allowed this;
  DELETE makes a swap easier (delete and recreate, rename into place). Open risk until a run's
  code is written to a folder only the server can write, granted read-only (`docs/plan.md`).
- Native code and Node still get the container's `AC\Temp` from Windows; only Python's
  `tempfile` is pinned.
- The old `write` ACE on `script-scratch` stays until the folder is swept; it is harmless.
- Files that earlier runs left in a workspace are not removed: they can't be told apart from
  the person's own files with certainty.
