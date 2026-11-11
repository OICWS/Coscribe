# The AI's browser keeps one layout whatever the panel's width (shipped)

Why: the browser panel is often dragged narrow during a workflow run. Sites
change their layout with the width (a menu folds behind a button, SAP's WebGUI
clips a toolbar), so a workflow made at one width could not find its buttons at
another. #884 widened the page only after a click missed; this makes the width
fixed while the AI works, and adds the checks automation tools make before a
click or scroll.

## Shipped
- While an AI turn or run uses a tab, the page lays out at least 1280 px wide,
  unscaled, until the turn or run ends (`TabCdp.fit`, `releaseTabs`). The panel
  shows the left part at the usual size; height follows the panel. A toolbar
  wider still widens the page to fit it, up to 2560 px (`TabCdp.widenTo`).
- A click on an element something else is laid over (a cookie banner, a
  dialog's backdrop) waits up to 2 s for it to go, then fails with what covers
  it, instead of clicking the overlay (`locate` in `browserAgentLocate.ts`).
- `browser_scroll` scrolls left and right too, and takes `within`: the ref of
  anything in the list, table or pane to scroll. A box that scrolls natively
  moves directly; one that scrolls by script (grids that draw their own
  scrollbar) gets a real mouse wheel; "nothing moved" is told as such instead of
  "already at the bottom" (`pageScroll` in `browserAgentPage.ts`).

Checked in Electron 42 under Xvfb, with a fake sidecar driving the real
`browserAgent` commands, panel 540 px wide, shown and closed. Seven scenarios
(clipped 1400 px toolbar, menu hidden below 900 px, cookie banner over a button,
virtual list in a side pane, script-scrolled grid, wide table, and styled
checkboxes, a fixed dialog and a sticky header that must not count as covered):
all pass in both modes; before today 1 of 7 passed with the panel shown. Public
pages: getbootstrap.com navigation passes before and after; on the AG Grid
100,000-row demo the grid scrolls down, and now right (before, "right" scrolled
down).

## Not verified
- On Windows, and on a real SAP WebGUI page.
- No agent benchmark (WebArena, WebVoyager) was run: they need a model driving
  the browser; the scenarios above script the tool calls instead.

## Follow-ups
- A horizontal scrollbar in the panel while the page is wider than it.
