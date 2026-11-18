# The workspace dialog on one page, and "environment" called a workspace in the UI (shipped)

Why: the dialog hid folders, network and secrets behind separate pages, and nothing showed that a
secret could never be sent because its host wasn't among the sites (#926, decision 0048).

## Shipped
- Edit workspace is one page: Name; Folder (the main one, with Change); More folders for this
  workspace (a table with Remove); Sites; Secrets; then Scripts and commands and Environment
  variables as before, on their own pages.
- Sites is None, Listed sites or Any site. Listed sites are added one at a time (normalized the
  way the server keeps them) into a table that shows which chosen secrets each site would get.
  Any site keeps scripts offline unless "Scripts may reach the internet too" is ticked (full).
- A chosen secret whose hosts none of the sites reach says so, with a button that adds its host.
  The matching is `lib/workspaceSites.ts`, tested in `workspaceSites.test.ts`.
- The UI says workspace where it said environment: Settings › Workspaces, the picker under the
  message box, the conversation menu, scheduled tasks. Code names and `/api/environments` stay.
- The Folders page's list of recent folders is gone with the page.

## Not verified
- On Windows: the native folder picker from Change and Add folder.

## Follow-ups
- A per-folder access level for a workspace's extra folders (the design shows one; the store
  keeps folders without one).
- The server's own refusals still say "environment's Network settings".
