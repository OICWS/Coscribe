# "Read, write and delete" folder setting; deletes go to the Recycle Bin (shipped)

Why: #560 makes the folder settings the one limit on what coscribe changes. Scripts already
can't delete or rename in any folder (the AppContainer grant has no delete right), and the file
tools deleted for good wherever they could write. The maintainer chose a third folder setting and
the Recycle Bin.

## Shipped
- Settings > Workspace > Other folders: each folder is Read only, Read and write, or Read, write
  and delete (`COSCRIBE_EXTRA_DELETABLE_DIRS`; Settings lists such a folder as writable too, so
  every place that writes needs no change).
- `delete_file` sends the file to the Recycle Bin (`send2trash`, as the Artifacts menu already
  does). It and `move_file`'s source work only in the workspace, the skills folder and folders
  set to Read, write and delete; a read-and-write folder refuses with a message naming the
  setting (`WorkspaceScope.resolve(delete=True)`).
- The model's list of folders says which ones allow deleting.
- Tests: `tests/test_files_tool.py` (refused in a read-write folder, allowed in a deletable one),
  `tests/test_config.py`, e2e `settings.spec.ts` (the third option saves).

## Not verified
- The Recycle Bin on a real Windows machine through `delete_file` (tests stand in for it; the
  same `send2trash` call already backs the Artifacts menu). On a network drive Windows has no
  Recycle Bin and deletes for good.
- Overwriting a file (`write_file`, `move_file` with `overwrite`) still replaces it in any
  writable folder; that is a write, not a delete.

## Follow-ups
- A conversation's own folders from Edit environment are read and write, so they refuse deletes
  unless the same folder is set to Read, write and delete in Settings.
