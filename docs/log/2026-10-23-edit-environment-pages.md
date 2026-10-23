# Edit environment is a list of pages, with the conversation's folders and Archive (shipped)

Why: issue #560 needs a place per conversation for its folders now, and for the scripts and
network settings next. Allen asked for the dialog in the shape of Claude's environment editor:
one row per part, each opening its own page, and no setting for messages from other
conversations (every conversation that is not archived can be reached; that change is its own
PR).

## Shipped
- `EnvironmentDialog.tsx`: a first page of rows (Folders, Secrets, Environment variables) with a
  summary each, a page per row with Back, one "Save changes" for every page, and "Archive
  conversation" (or Unarchive) at the bottom. The messages section and its client calls are gone.
- `components/environment/EnvironmentPages.tsx`: the pages. Folders ticks the conversation's own
  folders (the main one first, recent ones offered, Add folder… to browse); which folders exist and
  how far they may be used stays in Settings > Workspace.
- `GET`/`PUT /api/threads/{id}/folders`: a conversation that is not on screen; a live session is
  rebuilt the way `set_folders` does it, a closed one gets its sidecar. The one on screen still
  changes its folders over its socket, so its page shows the change.
- `lib/recentFolders.ts`: the recent-folder list both the picker and the page use.

## Not verified
- On Windows, and the Playwright specs locally: the E2E job runs them on this PR.

## Follow-ups
- The Scripts page (isolation check, Test again, run without isolation) and the Network access
  page come with their backends (#560, `docs/plan.md` item 4).
