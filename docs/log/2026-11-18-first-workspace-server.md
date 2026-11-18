# The first workspace: server part (shipped)

Why: a conversation with no folder worked in a hidden `workspace` under the app's data folder,
where what coscribe made piled up unseen (#926 phase C, decision 0048).

## Shipped
- `GET /api/workspace/first`: whether a workspace is still to be chosen (Default has no folder),
  the suggested folder (`Documents\Coscribe` in the home folder) and the hidden folder, when it
  holds anything besides `.coscribe`.
- `POST /api/workspace/first` with `folder`: makes the folder if its parent exists (a drive or
  the home folder itself is refused), and Default works there from now on, named for it.
- When the hidden folder holds files it becomes a workspace named "Earlier workspace", with
  Default's other settings, and the conversations and tasks that were on Default move to it, so
  each keeps the files it made. Nothing on disk moves or is deleted. Open conversations are told.
- A second choice answers 409: after that the workspace is changed in Settings › Workspaces.

## Not verified
- On Windows: a Documents folder redirected to OneDrive (the suggestion is `~\Documents`).

## Follow-ups
- The first-start dialog that calls these (the UI part).
- A conversation with no workspace only chats and asks for one before it saves a file.
