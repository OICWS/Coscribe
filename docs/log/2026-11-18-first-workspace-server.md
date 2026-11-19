# The first workspace: server part (shipped)

Why: a conversation with no folder worked in a hidden `workspace` under the app's data folder,
where what coscribe made piled up unseen (#926 phase C, decision 0048).

## Shipped
- `GET /api/workspace/first`: whether a workspace is still to be chosen (Default has no folder)
  and the suggested folder (`Documents\Coscribe` in the home folder).
- `POST /api/workspace/first` with `folder`: makes the folder if its parent exists (a drive or
  the home folder itself is refused), and Default works there from now on, named for it. Open
  conversations on Default are told.
- A second choice answers 409: after that the workspace is changed in Settings › Workspaces.
- No migration of the hidden folder's conversations or tasks: the app is still in development
  and what exists is test data (OICWS, 2026-11-18).

## Not verified
- On Windows: a Documents folder redirected to OneDrive (the suggestion is `~\Documents`).

## Follow-ups
- The first-start dialog that calls these (the UI part).
- A conversation with no workspace only chats and asks for one before it saves a file.
