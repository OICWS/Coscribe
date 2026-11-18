# 0048: A workspace is a folder the person picks; other folders are allowed when needed

Status: proposed (2026-11-16, OICWS: "like other agents, an office worker picks a workspace the
way a developer does, and what they make is kept there"). Builds on 0044; held to 0021; sites narrowed by 0050.

## Context
A conversation with no folder works in a hidden `workspace` under the app's data folder, where
made files, attachments and pasted pictures pile up unseen. Named environments already hold
folders, network, secrets and variables, but nothing says which folder is home. Other folders are
granted ahead of time in Settings, a page few people find; a chat that reaches outside its folders
gets only a text refusal, while a workflow run already stops and asks (`NeedsPermission`).

## Decision
- **Workspace.** A named environment becomes a workspace: one main folder the person chose, plus
  the network, secrets and variables it holds now. What coscribe makes goes in the folder;
  attachments and pasted pictures in `.coscribe/uploads/` (0044); notes, skills and later
  `settings.json` and `mcp.json` in `.coscribe/`. Conversation history, previews and secrets stay
  in the state folder, as Claude Code keeps sessions in `~/.claude`.
- **No hidden default.** The first start asks for a workspace (offered: `Documents\Coscribe`). A
  conversation without one only chats: its attachments go to the state folder and are deleted
  with it, and it asks for a workspace before it saves a file. An old hidden workspace holding
  files becomes a workspace named for it; nothing is moved or deleted.
- **Reach.** Code and file tools reach the workspace, the Allowed folders (Settings' list, every
  workspace), the folders allowed for this conversation or task only, and what scripts need to
  run (interpreter, scratch, skills). The AppContainer is granted exactly that set (0021).
- **Asked when needed.** A file tool refused outside that set shows a card in the chat (folder,
  access preset to the need): Allow adds it to Allowed folders; Only this chat keeps it to the
  conversation; a write also offers to save in the workspace. A workflow keeps its own: folders
  its steps name and those allowed while a run waited stay the task's.
- **Moving over.** An environment's first folder is its workspace; its other folders stay that
  workspace's only, never widened to all. A task on the old default needs a workspace before
  its next run, and says so. A watched folder must be within the task's reach.
- **Skills** stay as in Claude Code: installed ones global, `.coscribe/skills/` the folder's.

## Consequences
- Work stays with the folder the person manages; nothing grows unseen on C:.
- Folders on an SMB share still can't be reached by scripts (0021); file tools can.
- In phases, one PR each: A the chat card and Settings' Folder access; B uploads in
  `.coscribe/uploads/`; C the first start, no hidden default, moving environments and tasks;
  D `.coscribe/settings.json` and `mcp.json`.
