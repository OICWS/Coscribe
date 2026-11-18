# Settings › Environments as a table, and Allowed folders in a dialog (shipped)

Why: "Other folders" was still the label in Settings, a folder added there reached an open
conversation only after a restart, and the page did not read like the rest of Settings (#926,
decision 0048 phase A part 2).

## Shipped
- "Other folders" is called Allowed folders everywhere it is shown (Settings, the environment
  dialog's Folders page, the workflow permission text, the README).
- A change to Allowed folders applies at once: `web/routes/settings/config.py` sets the running
  settings and tells every open conversation, which rebuilds its folder tools on its next turn
  (`SessionReconfigurer.folders_changed`). Test:
  `tests/web/test_chat_folder_access.py::test_a_folder_allowed_in_settings_reaches_an_open_conversation_without_a_restart`.
- Settings › Environments lists the environments in a table (Name, Folder, Access, a ⋯ menu with
  Edit and Delete), titled with the count.
- Allowed folders is one row with Manage, which opens a dialog: a table of Folder, Location, Access
  and Remove; a folder that can't be opened now (an unplugged drive, an offline share) says so
  instead of offering access; Add folder opens the folder picker.
- The environment dialog's Folders page lists the allowed folders too, read only.

## Not verified
- On Windows: a network share and an unplugged drive in the dialog (checked here only with a
  missing local folder), and the native folder picker from Add folder.

## Follow-ups
- Allow on a chat's folder card adds the folder, but other open conversations see it only on
  their next rebuild; the Settings path notifies them, the card does not yet.
