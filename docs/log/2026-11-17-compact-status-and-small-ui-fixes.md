# Compact progress and small frontend polish (shipped)

Why: manual compaction took many seconds without feedback, and several small controls and the workflow investigation's intermediate page looked inconsistent.

## Shipped
- Show /compact's live elapsed time and final message-count/time summary in the existing composer status slot, without a second chat-log note. Block composer input and file drops while it runs. Normal turn timing returns on the next message.
- Make the Stop action a solid square icon-only button in Simple and Detailed workflow run views.
- Make Scheduled sort menus match their trigger width and center the sidebar View all action.
- Align Sessions title, optional group, environment and last-active columns; long names truncate with native hover titles.
- Show a dedicated "Handing off to AI…" screen while a failed run is being handed to its investigation conversation. No welcome greeting or composer appears during the handoff; the existing conversation view takes over when the first message arrives.
- "Create with Coscribe" opens an empty chat with the scheduled-task text prefilled and holds that layout after history loads, rather than remounting the composer inside a greeting screen and losing the draft. This only affects the seeded task-setup thread; ordinary New session greetings stay unchanged.

## Not verified
- UI behavior in the running desktop app, including an actual workflow investigation.
- During disconnect, compact's unconfirmed running indicator resets rather than claiming progress. A server-side operation status would be needed for full refresh/reconnect restoration.
