# The desktop title bar holds the conversation's name; panels stay at any width (shipped)

Why: the maintainer's review of the panel layout on Windows: icons larger and
window buttons paler than the reference, a divider that wasn't wanted, panel
edges too thin, and Task details (with its button) vanishing in a narrower
window.

## Shipped
- `App.tsx`: in the desktop shell the conversation's name (or the Scheduled
  breadcrumb) sits in the title bar after Back/Forward; the header row below
  it is gone, so the conversation starts higher. In a browser tab the header
  row stays as it was.
- Title bar icons are 16px with a finer stroke, in the text colour, in 32px
  buttons (`TITLE_BAR_ICON` in `lib/titleBar.ts`); the divider before
  Settings is removed.
- The OS window buttons are drawn in the text colour instead of the muted grey
  (`lib/titleBar.ts`, and the desktop's default before the page reports its
  theme, `main/windowChrome.ts`).
- Task details no longer closes, and its button no longer disappears, below
  1024px. The window's own minimum (960x620) is the limit.
- Side panels have a faint edge and a soft shadow (`--panel-edge`,
  `--panel-shadow`) instead of a plain 1px border.

## Not verified
- The Electron app on Windows: the window buttons' new colour and the title
  bar's spacing beside them.
