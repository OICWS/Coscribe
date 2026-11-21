# 0053: A workspace uses only the Allowed folders it picks

## Status
Accepted (2026-11-21, by the maintainer; proposed 2026-11-19, OICWS: "settings保留可以添加，但工作区需要选择用哪些，或者直接添加新的，两种方案").
Narrows [0048](0048-a-workspace-is-a-folder-the-person-picks.md), its reach only. Issue #926.

## Context
0048 let every workspace reach every folder in Settings' Allowed folders. A folder allowed for one
piece of work (a client's share, a finance drive) then reached every other workspace's
conversations and scheduled tasks too, and nothing in a workspace said which ones it reached.

## Decision
- **The list stays a library.** Settings › Allowed folders still lists folders, each with its
  access (read; read and write; read, write and delete), and folders are still added there.
- **A workspace picks.** A workspace's other folders (`folders[1:]` of its environment) are the
  ones it reaches besides its main folder. A folder picked from the library keeps the library's
  access; a folder added in the workspace itself joins the library as read and write.
- **Taking one off the library** takes it off every workspace that picked it, however its path
  is spelled, and from their open conversations before their next turn. The main folder is
  never taken off.
- **The chat card.** Allow adds the folder to the library and to the conversation's workspace (a
  conversation on Default first gets a workspace of its own, a scheduled run keeps it with the
  run); Only this chat keeps it to the conversation, as before.
- **What a conversation is told.** Its context names only its workspace's folders, each with its
  access; the folders in the library that the workspace didn't pick are not mentioned.
- **Scheduled tasks** reach their workspace's picks, and what a task's page shows is those.

## Consequences
- A folder allowed for one workspace no longer reaches the others; a workspace says what it
  reaches in one place.
- No migration: in development every workspace starts without picks (OICWS, 2026-11-19).

Retired wording: "Settings' list, every workspace"
