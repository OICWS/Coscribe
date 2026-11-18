# 0050: A workspace lists its sites, each with a browser level

## Status
Accepted (2026-11-18, OICWS). Narrows [0048](0048-a-workspace-is-a-folder-the-person-picks.md), sites only. Issue #926.

## Context
Two lists decide where the AI goes on the web. A workspace's Sites (`network.domains`) bound every
web tool, its browser included. The desktop app's global "Always allow" list
(`browser-settings.json`) only spares the built-in browser's prompt, in every workspace at once.
A person sees the two in different places, and a pre-allowed site that the workspace doesn't list
still fails. Secrets add a third list: the hosts each one may be sent to.

## Decision
- A workspace's site carries a browser level: **Use without asking**, **Ask each time** (a new
  site's default) or **Not in the browser** (web requests only: fetches, downloads, secrets).
  Kept beside the domains as `network.browser: {site: level}`; a site with no entry asks.
- With Any site, the table still lists sites, only for their browser level; an unlisted site asks.
  With None there are no sites and no browser.
- The backend sends each browser step the workspace's levels with its `network_sites`; the desktop
  app asks, allows or refuses from them. "Allow for this chat" stays in the app's memory only.
  "Always allow" on the prompt adds the site to the conversation's workspace as Use without
  asking, through the server, so it shows in Settings › Workspaces.
- The global list goes: Settings › Capabilities' Allowed sites and the panel's "Manage allowed
  sites…" open the conversation's workspace instead. On the first start of this version the app
  copies its list once into every workspace that reaches the site (Any site, or listed there), as
  Use without asking, then empties it.
- Secrets keep their own hosts (decision 0003); the dialog only shows which site gets which secret.

## Consequences
One place answers "where may this workspace go, and does it ask": Settings › Workspaces. A
scheduled task runs unattended on a site only if its workspace says Use without asking. A site
pre-allowed for one workspace no longer opens silently in another.

Retired wording: "always-allowed ones"
