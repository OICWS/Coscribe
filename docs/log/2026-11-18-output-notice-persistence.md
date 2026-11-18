# Closed file notices stay closed after restarting (shipped)

Why: the desktop app serves its UI from a different port each launch. File notice dismissals
in browser storage survived a reload, but disappeared when the application restarted.

## Shipped
- Store each closed file's path and modification time in the existing conversation metadata;
  merge dismissals and return them with activity. Other metadata updates preserve them.
- Load outputs and dismissals together so closed notices do not flash on reopening a conversation.
  A changed file returns as a notice; the original files and conversation history are untouched.
- Backend restart/isolation checks, the extended output-notices Playwright test, and fast checks
  pass. Two full Electron launches with different ports verified closed PDF, image and deck
  notices stay hidden and reappear after their modification time changes. The file list/history
  in that desktop check were fixtures; the app, persistence and restarts were real.

## Not verified
- A real Windows desktop locally; application restart checks used Electron on Linux.

## Follow-ups
- None.
