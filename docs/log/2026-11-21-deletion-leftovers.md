# Deleting a conversation leaves no blank Artifacts card or lingering sidebar row (shipped)

Why: #976, an Artifact card whose conversation was deleted opened a blank new conversation; #977,
a deleted conversation stayed in the sidebar until the server finished deleting it.

## Shipped
- Opening an artifact opens the viewer for the conversation it goes to, not the one the page was
  on (`setPanelOpen` takes the conversation), and a new conversation with a file open leaves the
  start page, which shows no panels (`App.tsx`).
- A card whose file is gone, or whose folder is no longer allowed, says so on the Artifacts page
  instead of doing nothing (`ArtifactsPage.tsx`, `lib/artifacts.ts`).
- A sidebar row shows "Deleting…" from the confirmation, leaves when the server is done, and says
  "Not deleted" when the delete failed (`lib/useThreadDeletion.ts`, `ThreadList.tsx`).
- e2e: `artifacts.spec.ts` (the viewer shows; the gone file's notice), `sidebar.spec.ts` (the
  deleting and failed states).

## Not verified
- The 8 seconds of #977 were not reproduced: here an idle conversation's `DELETE /api/threads/{id}`
  took about 5 ms. The likely wait is stopping a running turn (up to 15 s); not measured on
  Windows or on a long conversation.
- Not tried in the Windows desktop app.

## Follow-ups
- Time the server's delete on Windows with a long conversation and with a turn running.
