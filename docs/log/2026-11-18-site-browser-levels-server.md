# A workspace keeps a browser level per site, and the browser steps carry it (partly shipped)

Why: decision 0050 moves the built-in browser's global Always-allow list into each workspace's
sites. This is the server part; the desktop app and the UI follow.

## Shipped
- `network.browser` in an environment maps a site to `allow` or `off`; `ask` is the default and is
  not kept. `clean_network` checks it; a workspace with no internet keeps none.
- Every browser step sends `browser_sites` (the levels) beside `network_sites`. An older desktop
  app ignores it and asks as before.
- `POST /api/threads/{thread_id}/browser-site` sets a site's level in the conversation's
  workspace, refused for a site the workspace can't reach (the prompt's Always allow); audited.
- `POST /api/environments/import-browser-sites` adds the old global list once to every workspace
  that reaches each site, as `allow`, keeping a level a workspace already has.
- Tests: `tests/test_environments.py`, `tests/test_network_access.py`, `tests/web/test_settings.py`.

## Not verified
- Nothing applies the levels yet: the desktop app still asks from its own list until its PR lands.

## Follow-ups
- Desktop: decide from `browser_sites`, send Always allow to the server, import and empty the old
  list on first start. UI: a browser level column in the workspace's Sites.
