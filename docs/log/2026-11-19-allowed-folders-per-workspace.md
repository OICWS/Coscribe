# A workspace reaches only the Allowed folders it picks: the server (shipped)

Why: decision 0053 (#926). Every workspace reached every folder in Settings' Allowed folders, so
a folder allowed for one piece of work reached all the others.

## Shipped
- A workspace's other folders are the Allowed folders it reaches, each with the library's access;
  one the library doesn't list is read and write. Code, file tools, the edit preview, workflow
  drafting and a scheduled run all take their reach from `Settings.reach_of`.
- Creating or saving a workspace, or adding a folder from the chat, puts its new other folders
  in the library as read and write (not one with a comma in its path, which the list can't
  hold). Taking a folder off the library takes it off every workspace (never a main folder)
  and off their open conversations before their next turn. Folders are compared by one
  spelling (`~`, links, `/` or `\`, case on Windows).
- The chat card's Allow adds the folder to the library and to the conversation's workspace, and
  the open conversation reaches it at once. A conversation on Default gets a workspace of its
  own first; a scheduled run keeps the folder with the run.
- A conversation is told only its own folders, each with its access; the old system-prompt
  note listing every Allowed folder is gone.
- A scheduled task's reach lists the workspace's picked folders, not the whole library.

## Not verified
- On Windows with real folders and the desktop app; the tests use temporary folders.

## Follow-ups
- The workspace dialog: pick folders from the library, or add a new one (frontend).
- A folder allowed on the card reaches other conversations already open in the same workspace
  only from their next session.
- A folder outside the library (a scheduled task's own, one the list can't hold) reads and
  writes; the workspace dialog could say so.
