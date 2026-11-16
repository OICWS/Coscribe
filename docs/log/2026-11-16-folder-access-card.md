# The model asks for a folder outside the workspace on a card in the chat (partly shipped)

Why: a file tool refused a path outside the workspace and the person had to find Settings' other
folders on their own. Decision 0048, phase A part 1 (#926).

## Shipped
- `request_folder_access` (a question tool, `tools/bookkeeping/interaction.py`): the refusal in
  `tools/_workspace.py` now tells the model how to call it.
- The card (`frontend/src/components/chatlog/FolderAccessCard.tsx`): Allow adds the folder to
  Allowed folders (the `.env` keys Settings edits, live in the running server); Only this chat
  keeps it in `environments.json` for the conversation, cleared with it; a write request also
  offers saving in the workspace; Don't allow, or a reply typed in the chat, refuses.
- After an allow the conversation's tools are built again before the turn goes on, so the
  refused call reaches the folder (`conversation/folder_access.py`, `reconfigure.py`).
- A drive root, the home folder or a folder that holds it is never offered (`Environments.too_broad`,
  shared with the scripts' blocked-folder offer), nor a path with a comma, which the `.env` list
  can't hold. Allow merges into what `.env` holds now, and each answer is audited.

## Not verified
- A real Windows machine: the card, a folder path with a drive letter, and the `.env` written
  next to the installed server.

## Follow-ups
- Settings' Folder access (phase A part 2, `docs/plan.md`).
- The answered card has no Undo; the side panel's workspace scope doesn't list chat-only folders.
- A script refused a folder still shows its own blocked-folder card; a workflow step without the
  tool may still read the hint.
