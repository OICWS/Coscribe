# Named environments, chosen below the message box (shipped)

Why: each conversation kept its own folders, network, secrets, variables and "run without
isolation", set one by one from its right-click menu. Allen asked for environments to name once and
pick from the composer, the same everywhere (#588, step 3 of 4).

## Shipped
- `runtime/environments.py`: `environments.json` holds the environments and which conversation uses
  which. Each holds a name, folders, network, secrets, variables, `scripts` and `commands` switches
  that only narrow Settings › Capabilities, and `unisolated`. Default can't be deleted; deleting
  another moves its conversations to Default. Names are unique.
- Every reader goes through it: `SessionEnvironments`, `NetworkAccess`/`NetworkGuard`,
  `UnisolatedConversations`, `require_capability(…, thread_id)` and a conversation's folders
  (`ThreadFiles.folders_of`). Scheduled runs keep their task's folders for now.
- First start: each conversation's settings from before become an environment named after its title
  (or first message), conversations with the same settings share one, and those with none stay on
  Default (`web/environment_migration.py`). The old files are left in place, unread.
- `GET/POST /api/environments`, `PUT/DELETE /api/environments/{id}`. A change to network, the
  switches or `unisolated` is an audit entry (`set_environment`). A folder change moves the open
  conversations using it at once, and is refused (409) while one of them is running a turn.
- The socket's `set_folders` became `set_environment`, refused while a turn runs. `add_folder`
  ("Add folder" on a blocked-folder card) adds to the environment; on Default the conversation gets
  an environment of its own, so the folder isn't opened to every conversation.
- The composer's folder picker became the environment picker: search, a checked list, a gear per
  environment, New environment. The dialog edits an environment ("Used by N conversations", Scripts
  and commands page, Delete environment). The desktop menu's Open Folder… is Choose Environment….
- `GET /api/threads/{id}/environment|folders|network|scripts` are gone; the settings routes for
  environments are in `web/routes/settings/named_environments.py`.

## Not verified
- On Windows: the picker, the dialog and the move of real settings were not clicked through on a
  Windows machine; the e2e specs run in CI on Linux.
- The move ran only on test data, not on a long-used state folder.

## Follow-ups
- Scheduled tasks choose an environment (#588).
- Commands in Codex's Windows sandbox (#588, step 4).
