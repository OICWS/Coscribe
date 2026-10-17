# Any panel opens in a window of its own (shipped, desktop)

Why: with Task details, Browser, Background tasks and the viewer (and artifacts to come) sharing
the main window, a panel needs to live beside it on another screen. The maintainer's reference was
Claude's "Open in new window" in a panel's Move menu, with "back to the main window" and "keep on
top" in the new window's title bar.

## Shipped
- **Opening**: the panel's expand menu (Move, Fill and arrange) ends in "Open in new window", in
  the desktop app only. The window opens at the panel's place and size on screen.
- **The panel's own window**:
  - the panel's header is the window's title bar;
  - beside the OS buttons are "Return to the main window" and "Keep on top" (a pin);
  - the OS buttons are centred on the header row, whatever its height.
- **Coming back**: "Return to the main window" puts the panel back where it was. The window's close
  button closes the panel.
- **Main window**: a panel in its own window is left out of the main layout. Its title-bar switch
  stays on and brings that window to the front.
- **Data**: the main window keeps the conversation and its socket, because a second socket to the
  same conversation would take its live updates.
  - It sends each panel's data through the desktop shell (`main/panelWindows.ts`).
  - The panel's window sends back what the user does: open a file, approve a step, send a capture
    to the chat, stop the AI. A panel in its own window follows the main window's conversation.
- **Browser**: its tab views move to the window showing the panel. Only that window can move or
  close them, so the two windows can't race. Its menu and the AI's steps reach that window.
- **Checks**: `tests/e2e/panel-windows.spec.ts` stands in for the shell with two pages relaying
  through a BroadcastChannel. It fails when "Open in new window" is disconnected.

## Not verified
- The real Electron windows on Windows:
  - window placement on a second display;
  - the OS buttons' height on each panel's header;
  - dragging the window by the header;
  - "Keep on top";
  - the browser's tab views moving between windows.
- Only a simulated shell was tested here; the Electron binary can't run in this container.

## Follow-ups
- The artifact panel will use the same mechanism.
