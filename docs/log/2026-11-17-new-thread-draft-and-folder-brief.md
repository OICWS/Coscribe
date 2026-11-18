# A new conversation opens in its final layout, the folder brief folds away, the batch bar is centered (shipped)

Why: the maintainer reported three UI issues on 2026-11-17. "Create with Coscribe" on the
Scheduled page showed the chat layout with "I'd like to set up a scheduled task: " in the message
box, then switched to the greeting with an empty box. The side panel's "About this folder" brief
read as noise. The sidebar's Move, Archive and Delete sat left of center.

## Shipped
- `lib/nav.ts`: `startNewThread` remembers the threads it started (`useFreshThread`), and `App.tsx`
  shows the new-conversation layout for one before its empty history arrives, then forgets it.
  The composer used to mount in the chat layout, take the prefilled draft and be remounted empty
  when the layout switched; checked live with Playwright (before: chat layout with the draft, then
  the greeting with an empty box; after: the greeting with the draft from the first frame).
- `TaskPanel.tsx`: the folder brief is folded under "What Coscribe knows about this folder"
  (collapsed by default, tooltip says it is written from the file names only). A folder's
  `.coscribe` notes still show unfolded, since they need the person's yes.
- `BatchBar.tsx`: the action row is centered, and the Move menu opens centered above it.

## Not verified
- A real Windows machine and the Electron shell.

## Follow-ups
- None.
