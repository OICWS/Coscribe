# Sidebar sessions can be selected in bulk (shipped)

Why: the sidebar could only act on one conversation at a time, so clearing out or
grouping many of them meant repeating the same menu steps.

## Shipped
- "Select" in a conversation's "..." menu turns the list into multi-select mode:
  each row gets a checkbox, clicking a row toggles it, Escape or Cancel leaves.
- A bar under the list acts on the selection: Move to group (existing, new or
  Ungrouped), Archive/Unarchive, Delete (one confirmation for all). Rename, Edit
  environment and Export conversation are not offered because each works on one
  conversation.
- `ThreadList` and `NavRail` (`onDeleteRequest` now takes a list).

## Not verified
- Not run in a live browser or on Windows; only `npm run build` and oxlint.
- No Playwright spec for the new mode.

## Follow-ups
- An e2e spec for select, batch archive and batch delete.
