# Settings headers stay aligned when a page scrolls (shipped)

Why: Skills has enough content to show a 12 px scrollbar, while shorter Connectors and
Providers pages do not. That shifted the Skills search field and Add button left.

## Shipped
- Reserve a stable scrollbar gutter on the shared Settings content pane. Headers retain
  the same available width when switching pages or changing search results.
- Full Electron app measurements reproduced the 12 px shift before the fix and verified
  identical search/Add bounds afterward, using the actual three settings pages.
- The Allowed folders browser test creates its own temporary directory and removes it
  afterward, so it exercises access controls rather than the missing-folder notice.

## Not verified
- A real Windows desktop locally; screenshots and layout checks used Electron on Linux.

## Follow-ups
- None.
