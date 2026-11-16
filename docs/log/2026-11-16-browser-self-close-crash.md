# A page that closes itself no longer crashes the desktop app (shipped)

Why: after a workflow's web automation, closing its page threw "Cannot read properties of
undefined (reading 'isDestroyed') at closeTab" in the main process. When a page closes itself
(`window.close()`, a site's own close or logout button), Electron clears the view's
`webContents` before the "destroyed" event reaches the panel, and `closeTab` read it.

## Shipped
- `closeTab` (`office-agent-desktop/src/main/browserPanel.ts`) closes the page only while the
  view still has a live `webContents`; the rest of the tab removal is unchanged.
- `scripts/browser-native.cjs` opens a popup in real Electron, has it call `window.close()`
  and fails on any uncaught main-process error; it reproduced the reported message before the
  fix. The transport double in `scripts/browser-regression.cjs` now drops the view's
  `webContents` on destroy the way Electron 42 does, so its site-closed-page check also fails
  without the fix.

## Not verified
- The exact page in the reported workflow and a person using the Windows app. Both scripts
  pass under Linux/Xvfb; the native one also runs in the Windows desktop smoke job.

## Follow-ups
- Whether a workflow run's pages close when the run ends is a product decision; listed for the
  maintainer in `docs/plan.md`.
