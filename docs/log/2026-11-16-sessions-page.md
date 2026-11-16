# A Sessions page lists every conversation, opened from the sidebar's "View all" (shipped)

Why: the sidebar shows recent conversations only, with no full page to browse or search them all.

## Shipped
- "View all" under the last conversation in the sidebar (`components/ThreadList.tsx`) opens
  `?view=sessions` (`lib/nav.ts` `showSessions`).
- `components/sessions/SessionsPage.tsx`: title "Sessions", Active / Archived tabs, a search
  button (title or environment name) and "New session" on the right, and one row per
  conversation with its title, the name of the environment it uses and how long ago it changed
  ("8 minutes ago"), newest first. A row opens that conversation.
- `lib/sessionList.ts` holds the tab, search and relative-time logic, covered by
  `lib/sessionList.test.ts`.
- To stay inside the line ratchet, the Background tasks button's title moved into
  `useRunningBackgroundTasks`, and the sidebar's folded groups into `useCollapsedGroups`.

## Not verified
- The Electron app on Windows; checked in Chromium against a mocked backend (screenshots in the PR).
