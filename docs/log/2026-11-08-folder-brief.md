# The model knows what a folder holds from the first message (shipped)

Why: step 5 of the agentic plan (#819), approved by the maintainer on 2026-11-08. A conversation that works in a folder began by listing it, in every conversation, before it knew where the templates, the data and the finished work were.

## Shipped
- `conversation/folder_brief.py`: the side model writes two or three sentences on what a folder is for, which parts are templates, data or finished work, and how files are named. It reads only the file names, types and counts, two levels deep (at most 400 entries, tools' own folders such as `.git` and Office lock files left out); it opens no file.
- The brief is kept per folder in `folder-briefs.json` in the state folder, shared by every conversation that works there, and written again when the names at the top of the folder change. An empty folder gets none.
- It is written in the background when a conversation opens, when a folder is attached and at a message whose folder has none (a failed call waits for the folder to change or for "Read again"), so it never holds up a turn; the model reads it in the conversation's context beside the folder's path (never in the system prompt). A brief missing at the first message comes with the next one.
- Side panel, Context: "About this folder" (or "About these folders", each named) shows the brief with a "Read again" link (`POST /api/threads/{id}/folder-brief`). The panel looks again every 3 s while a brief is being written.
- `Settings.folder_briefs` (`COSCRIBE_FOLDER_BRIEFS`, on by default) turns the automatic briefs off; "Read again" still writes one.
- Tests: `tests/test_folder_brief.py` (the listing, the signature, the store, when a brief is written, turned off, a failed call), `tests/web/test_thread_activity.py` (the activity's folders and the route).

## Not verified
- A real Windows machine, and a large or slow network folder (the listing stops at 400 entries, but a slow share still costs the scan).
- How well a small model other than DeepSeek's describes a folder.

## Follow-ups
- A switch for `COSCRIBE_FOLDER_BRIEFS` in Settings > Sessions.
