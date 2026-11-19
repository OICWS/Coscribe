# The first start asks for a workspace (shipped)

Why: until a workspace was chosen everything coscribe made went to a hidden folder under the
app's data folder (#926 phase C, decision 0048). The server part is
`docs/log/2026-11-18-first-workspace-server.md`.

## Shipped
- While Default has no folder, the app opens on "Choose a workspace": the suggested folder
  (`Documents\Coscribe`), Change… (the native picker in the desktop app, the folder browser in a
  tab) and Use this folder. A refusal (a missing parent, a drive) shows under the folder and the
  dialog stays. After the choice the page reloads in the new workspace.
- The dialog is mounted beside `App` in `main.tsx`, so `App.tsx` is unchanged.
- The e2e workflow chooses its scratch workspace with the same call before the specs, and the
  desktop smoke answers it as chosen, so neither sees the dialog. `first-workspace.spec.ts` plays
  the first start with both calls answered by the test; the specs that named "Default" read its
  name now (`defaultWorkspaceName` in `tests/e2e/helpers.ts`).

## Not verified
- On Windows: the native folder picker from Change…, and a Documents folder on OneDrive.

## Follow-ups
- A conversation with no workspace only chats and asks for one before it saves a file.
