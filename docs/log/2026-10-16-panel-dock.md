# Several side panels at once, arranged by dragging (shipped)

Why: the maintainer wants Task details, Browser and Background tasks open
together, each a window of its own that can be moved, resized and filled,
before the file viewers join them as panels (#334).

## Shipped
- `components/dock/PanelDock.tsx`: the panels beside the conversation, laid
  out from the split tree in `lib/dockLayout.ts` (#335) as one flat list of
  absolutely placed boxes, so moving a panel never remounts it.
  - **Dragging a header** (or the grip at its top) moves the panel. The drop
    place shows as a blue line on the edge it will land on.
  - **Gaps** between panels, and between the conversation and the panels,
    resize. The line in a gap darkens under the pointer, as the scrollbars do.
  - **Remembered**: the arrangement is kept on this computer. A closed panel
    comes back beside the panel it sat next to.
- **Opening a panel** adds a column while the conversation keeps 560px,
  otherwise stacks it under the rightmost panel.
- **Too narrow:** when the conversation would get less than 380px, the panels
  cover it.
- `components/dock/DockControls.tsx`: each panel's expand and close buttons.
  - **Hovering expand** opens Move (left, right, top, bottom of everything)
    and Fill and arrange (fill the window, side by side, stacked).
  - **Clicking expand** fills the window; Escape restores.
- `App.tsx`: which panels are open is a set per conversation, not one panel at
  a time. Task details stays shut below 1024px wide, as before.
- `DesktopBrowserPanel.tsx`:
  - While a panel is dragged or a Move menu is open, the live page (an OS
    view above the window) is replaced by a captured picture, so the drop line
    and the menu are not hidden under it.
  - The view follows the panel when it moves, not only when it resizes.
  - Its own resize handle and expand are gone; the dock's replace them.
- `usePanelWidth.ts` removed.

## Not verified
- The Electron app on Windows: the native browser view following a moved
  panel, and the captured picture standing in while dragging. Here the desktop
  bridge was simulated, and the calls were checked (capture, view hidden,
  reposition).

## Follow-ups
- The file viewers (Word review, slides, sheets) as panels.
- Opening a panel in a window of its own.
