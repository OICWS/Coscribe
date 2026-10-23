# The person chooses which title-bar buttons stay; the rest sit in a menu (shipped)

Why: the Plan button showed only while a conversation had a plan or a task list, so it looked
as if it had gone, and more buttons were coming. Issue: #565.

## Shipped
- `lib/toolbarItems.ts`: the six items (Sidebar, Artifacts, Task details, Plan, Browser,
  Background tasks), the defaults (all pinned except Artifacts), and the pinned list kept in the
  browser (`lib/storage.ts`), so per device. Unknown or unreadable stored values fall back to the
  defaults; a stored empty list stays empty.
- `PanelToggles` draws the pinned items as buttons and gives the rest to `ToolbarMenu` (new): a
  down-arrow button, which every page has, listing the unpinned items and "Edit toolbar". Panels
  are offered only inside a conversation. Plan is always a button when pinned; its panel already
  says "No plan in this conversation yet".
- `ToolbarDialog` (new): a checkbox per item and Done.
- `NavRail` hides the sidebar's own button when Sidebar is unpinned; the menu then shows
  "Show sidebar" / "Hide sidebar".
- `tests/e2e/toolbar.spec.ts` (in the nightly list) and `lib/toolbarItems.test.ts`.
- Ratchet accepted growth in `App.tsx` (+7 lines) and `NavRail`.

## Not verified
- The desktop title bar on Windows (the tests run the page header). With Sidebar unpinned the left
  cluster is one button shorter and its reserved width is unchanged, so a small gap sits beside it.
- An item added later is not in a stored list, so it starts in the menu, not on the bar.

## Follow-ups
- None.
