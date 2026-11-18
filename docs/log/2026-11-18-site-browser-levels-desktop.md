# The desktop app's browser follows the workspace's level for each site (partly shipped)

Why: decision 0050 gives each workspace site a browser level; the desktop app decides each
browser step. This is the desktop part; the UI follows.

## Shipped
- A browser step reads `browser_sites` from the server: Use without asking goes ahead with no
  prompt, Not in the browser is refused with a reason the model reads, and any other site asks
  as before (`browserPermissions.ts`, `siteLevel` and `checkSite`). The most specific site wins,
  so admin.example.com can stay out while example.com is allowed.
- The app's own Always-allow list still counts until the UI moves it into the workspaces.
- Tests: the site levels in `scripts/browser-regression.cjs` (`npm run test:browser`).

## Not verified
- On Windows, in the real app: a prompt-free step on a Use without asking site and a refused step
  on a Not in the browser site.

## Follow-ups
- UI: a browser level column in the workspace's Sites; Always allow on the prompt writes to the
  workspace; the old list moved once and Settings › Capabilities' Allowed sites removed.
