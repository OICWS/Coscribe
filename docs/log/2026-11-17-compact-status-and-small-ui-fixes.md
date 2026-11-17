# Compact progress and small frontend polish (shipped)

Why: manual compaction took many seconds without feedback, and several small controls and the workflow investigation's intermediate page looked inconsistent.

## Shipped
- Show /compact's live elapsed time in the composer status slot. On completion, retain the conversation and show one small text notice with estimated tokens saved, without horizontal rules. Internal summaries and task notes are never replayed to the UI, with no expansion control. Reopening preloads the preceding conversation segment and preserves images; earlier segments still page on demand.
- Make the Stop action a solid square icon-only button in Simple and Detailed workflow run views.
- Make Scheduled sort menus match their trigger width and center the sidebar View all action.
- Align Sessions title, optional group, environment and last-active columns; long names truncate with native hover titles.
- Show a dedicated "Handing off to AI…" screen while a failed run is being handed to its investigation conversation. No welcome greeting or composer appears during the handoff; the existing conversation view takes over when the first message arrives. A late response does not navigate after the user leaves.

## Not verified
- Authenticated workflow investigation; the full Electron app's compaction/reopen/image flow was checked with fixture messages and captured locally, without screenshot uploads.
- During disconnect, compact's unconfirmed running indicator resets rather than claiming progress. A server-side operation status would be needed for full refresh/reconnect restoration.
