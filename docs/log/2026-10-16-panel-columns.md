# Panels on either side of the conversation, with a live preview while dragging (shipped)

Why: the maintainer's review of #334 on Windows: the conversation should make
room when a panel is put beside it (not only on its right), a drag should show
where everything will go before the button is let go, and a narrow window
should never close a panel.

## Shipped
- `lib/dockArrangement.ts` (new):
  - **Columns:** the window is columns of side panels on either side of the
    conversation. The conversation takes the width they leave; each column
    keeps its own width in pixels, so resizing the window changes the
    conversation, not the panels. Each column holds the split tree of
    `lib/dockLayout.ts` (whose single-area functions it replaced are gone).
  - **Drop places:**
    - beside a panel, on its nearest edge;
    - either half of the conversation, which makes a column on that side
      of it;
    - near the window's edge, which makes the outermost column.
  - **Move menu:** left and right make an outermost column. Top and bottom
    stack the panel along that edge of its own column, or of the nearest
    other one when it is alone.
  - **Closed panels** come back where they were: beside the same neighbour,
    or as the same column.
- `components/dock/PanelDock.tsx`:
  - **Placement:** the conversation is placed by the layout like a panel.
  - **Preview:** while a panel is dragged, the other panels and the
    conversation slide (150ms) to where they will be, and the dragged
    panel's new place shows as a dashed outline.
  - **Resizing:** gaps resize the panels inside a column, and a column
    against its neighbour.
- **Narrow windows:** columns give up width down to 280px before the
  conversation goes below 380px; past that the panels lie over the
  conversation instead of closing.
- **Saved layouts:** a layout saved by the previous version is read as one
  column on the right.

## Not verified
- The Electron app on Windows: the feel of the moving preview, and the
  desktop browser view following a panel into a left column.
- In a browser tab with the sidebar unpinned, a panel in a left column sits
  under the sidebar's 48px toggle; the desktop shell keeps that toggle in the
  title bar, so it is not affected.
