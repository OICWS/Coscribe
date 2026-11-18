# A task shows what it can reach, and its folder inputs are checked against it

Why: decision 0048 has a scheduled task show what it reaches, pick its folder inputs from that,
and allow a folder outside it before a run would stop to ask.

## Shipped
- The task page's settings show "What this task can reach": its workspace, Settings' Allowed
  folders, and each folder allowed for this task only, which can be removed there
  (`TaskReachSection.tsx`).
- On a saved task's page, a folder input (Run now, an input's usual value, an ask step) can be
  typed or pasted, or picked from a menu of the workspace's folder and its subfolders, the Allowed
  folders and this task's own, or any folder (`workflow/FolderValue.tsx`).
- What is typed or picked is checked against the reach (`POST /api/reach/check`). Inside, a line
  says where; a read-only allowed folder says a run that saves there stops to ask. Outside, a card
  offers Only this task, Allow everywhere (Settings' Allowed folders, read and write) or Pick
  another folder. A value worked out from another input or a step isn't checked.
- Read-only allowed folders stay pickable, labelled Read only: a folder input may be read from.
- Tests: `tests/e2e/task-reach.spec.ts`.

## Not verified
- On Windows: a drive letter, a share, and the native folder picker from Choose another folder.

## Follow-ups
- A task not saved yet has no picker: its folder inputs are set once it is saved.
