# Scripts' folder grants are taken off folders no longer in use, and at uninstall (shipped)

Why: issue #560, part 3c. The ACE written on a folder for scripts' isolation stayed after the
person removed the folder from Settings or deleted the conversation that used it, and after
coscribe itself was uninstalled.

## Shipped
- `FolderGrants.sweep(keep)` and `sweep_folder_grants(state_dir, folders)` in
  `tools/exec/isolation.py`: every grant on a folder outside `folders` is revoked. What the
  interpreters read is kept: the script venv and the Python it was made from, `node-env`, the
  scratch folder and Node's own folder. A self-test's folder, deleted after the test, leaves the
  registry. `None` revokes every grant.
- `web/folder_grants.py`: the folders in use are the workspace, the skills folder, the extra
  folders in Settings and every conversation's folders. The server sweeps once at each start, in
  a thread, since icacls on a big folder takes a while.
- `coscribe-server --revoke-folder-grants` revokes every grant and exits. The NSIS uninstaller
  runs it (`customUnInstall` in `office-agent-desktop/build/installer.nsh`), but not for the
  uninstall step of an update.

## Not verified
- The uninstaller on a real Windows machine (CI builds no installer). The sweep itself is tested
  with icacls faked; the Windows job runs the real grant tests.

## Follow-ups
- coscribe's own Python download (`docs/plan.md` item 4).
