# The desktop shell starts the server before Electron is ready (shipped)

Why: #478 part 2. The server needs about 2 s and nothing from Electron, but it was spawned
only after `app.whenReady()`, and the window polled for it every 300 ms.

## Shipped
- `office-agent-desktop/src/main/index.ts`: the free port and the sidecar spawn start at module
  load (after the single-instance lock); `whenReady` waits for them. The kill on quit, the lock
  and the tray are unchanged.
- `mainWindow.ts`: the readiness poll is 50 ms instead of 300 ms. The splash already showed at
  once (`loadFile` in `createMainWindow`), so nothing moved there.
- `office-agent-desktop/scripts/measure-startup.mjs`: launches the shell and reads the window's
  URL through Chromium's remote-debugging endpoint; "app" is the first time the window is on the
  server's page.
- Time to a window on the server's page, unpackaged Electron 41 under Xvfb on Linux, the PyInstaller
  sidecar, 8 runs each: 2.87 s (range 2.23-3.21) to 2.22 s (2.11-2.66). The splash shows at
  0.43 s either way.

## Not verified
- The installed app on Windows (Defender's first-run scan, a cold disk). The runs are on Linux, in
  the unpackaged shell, with the before runs taken first.
- The shutdown path was not exercised beyond the build; `desktop-smoke` in CI covers a launch.

## Follow-ups
- None for #478 beyond the Windows numbers.
