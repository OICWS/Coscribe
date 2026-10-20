# An Electron smoke test runs on the Windows runner (shipped)

Why: issue #472, item 3. Whether the desktop shell starts its sidecar, loads the UI and quits
cleanly was only checked by hand on Windows.

## Shipped
- `office-agent-desktop/scripts/smoke.mjs` launches the built shell through Playwright's Electron
  driver (taken from the frontend's packages, so no new dependency) with a stub provider in a
  temporary app-data folder, and checks: the sidecar answers and the window navigates to it; the
  page draws its title bar ("Menu", "Settings") and the preload reports the platform; closing the
  window exits the app and the sidecar stops answering.
- `desktop-smoke.yml` runs it on `windows-latest`, nightly and on a pull request that touches the
  shell.
- Proved by breaking it: with `window-all-closed` not quitting, the last step fails ("still running").
  Run under xvfb on Linux in the cloud session, all three steps pass.

## Not verified
- The run on `windows-latest`.
- The packaged app: the PyInstaller sidecar and the installer are not built here (that is
  `desktop-build.yml`, manual); the shell runs as `electron .` with the pip-installed `coscribe-web`
  as sidecar. The packaged `win-unpacked` exe takes the same code paths, but the sidecar lookup differs.

## Follow-ups
- A step that runs the packaged `win-unpacked/coscribe.exe` the same way, if the maintainer wants it
  in nightly CI.
