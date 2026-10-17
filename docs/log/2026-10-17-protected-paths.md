# The file tools cannot write coscribe's own settings files (shipped)

Why: #402 item 2, the gap the prompt-injection threat model (#395) found. With the workspace, the
state folder and the settings files as siblings (the desktop layout) the file tools cannot reach a
policy. A user who picks a folder that contains them as the workspace, or points a setting into it,
let `write_file` change the exec policy or hooks, and Accept Edits writes without asking.

## Options considered
- Refuse writes to coscribe's own files in `WorkspaceScope` (chosen): small, covers every path the
  file tools take, symlinks included, and does not depend on where the user keeps things.
- Ask on every write to such a file: the card would look like any other edit, and Accept Edits is
  the mode that skips cards.
- Move all settings out of any folder a user can pick: not enforceable, the paths are the user's.

## Shipped
- `WorkspaceScope(protected=...)` refuses `write=True` resolutions under a protected path.
- `Settings.protected_paths()`: the state folder, memory file, MCP, hooks, providers and exec-policy
  files, and `.env`. The coordinator passes it to the file tools.
- `tests/test_protected_paths.py` (9 cases; 8 fail with the check off).

## Not verified
- The office, image and slide-engine toolkits are not given the list: they write only files with
  their own extensions (.docx, .xlsx, .pptx, images), never JSON or Markdown settings. The slide
  engine is also another session's area.
- Reading a settings file is still allowed.

## Follow-ups
- None.
