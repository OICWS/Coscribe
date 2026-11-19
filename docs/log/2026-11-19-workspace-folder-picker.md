# A workspace picks its Allowed folders in its dialog (shipped)

Why: decision 0053 (#926). The server keeps a workspace to the Allowed folders it picks; the
workspace dialog now lets the person pick them.

## Shipped
- The workspace dialog's "Allowed folders this workspace uses" lists each picked folder with its
  access from Settings. "Use an allowed folder" picks one from the list; "Add new folder…" adds a
  folder that joins Allowed folders as read and write when the workspace is saved.
- An open Settings reloads Allowed folders after a workspace is saved, so saving its own older
  copy can't take the new folders off again.
- The chat card says Allow adds the folder to this workspace and to Allowed folders; Settings'
  Allowed folders row and dialog say a workspace reaches only the ones it picks.

## Not verified
- In the desktop app on Windows; checked in Chromium against a local server with a stub model.

## Follow-ups
- `conversation/wire.py` still describes the card's `allow:<access>` answer as "every workspace".
