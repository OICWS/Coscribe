# A workspace's Sites table sets each site's browser level

Why: decision 0050 keeps the built-in browser's site permissions in the workspace, beside its
sites, instead of in a global list the desktop app kept on its own.

## Shipped
- Edit workspace › Sites has an "In the browser" column: Use without asking, Ask each time or Not
  in the browser, saved as `network.browser` (`WorkspaceSections.tsx`, `useNetworkDraft`). With
  Any site the table lists only the sites given a level.
- The Browser panel's Always allow keeps the site in the asking conversation's workspace
  (`POST /api/threads/{id}/browser-site`) and lets this step go ahead for the conversation; if the
  server refuses, the app's old list keeps it as before.
- ⋮ → "Manage allowed sites…" opens the conversation's workspace. Settings › Capabilities' Allowed
  sites and `AllowedSitesDialog` are gone; Settings search finds sites under Workspaces.
- On start the app's old list moves once into the workspaces that reach each site
  (`lib/oldAllowedSites.ts`), and is emptied once the server kept it.
- Tests: `tests/e2e/rail-dialog.spec.ts` sets a level in the table and reads one kept by the route.

## Not verified
- On Windows, in the real app: Always allow on the prompt, the menu entry opening the workspace,
  and the old list moving on the first start.

## Follow-ups
- The desktop app's global list, its IPC and its fallback in `isAllowed` can go once every install
  has moved its list.
