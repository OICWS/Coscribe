# Sandboxed commands can't read the person's private folders (shipped)

Why: Codex's sandbox setup lets its users read every folder of the person's profile, so a
sandboxed command could read Documents, Desktop, Downloads and AppData (#601, part of #588).

## Shipped
- A new Settings › Capabilities switch, "Hide your private folders from commands", on by default:
  `commands_hide_private_folders`.
- While it is on, the permission profile denies Documents, Desktop, Downloads, Pictures, Videos,
  Music, OneDrive, AppData and `.ssh`/`.aws`/`.azure`/`.kube`/`.docker`/`.gnupg`. The known
  folders come from the known-folder API, so a redirected folder is found. Codex itself applies
  and keeps the deny-read entries (`tools/exec/_private_folders.py`).
- A folder the environment was given is never denied, and a deny Codex left on it is taken off.
- coscribe grants read, off the event loop, on the read-only folders, the batch files and the
  PATH folders that lie inside a denied one. A failed grant stops the command and says why.
- A command has its own TEMP/TMP in the state folder.
- A ledger, written whole before each change, lists every folder denied or granted. Turning the
  switch off, or removing the sandbox (also when its Codex is gone), clears them and checks with
  icacls. Folders it couldn't clear are reported and kept for the next try.
- Decision 0022 updated: what is hidden, and that other drives and Windows' folders stay
  readable. An online sandboxed command still goes to the person.
- Real-Windows check (`test_windows_real.py`):
  - A command in a Documents workspace can't read a file beside it, on the Desktop or in
    Roaming, and Python's tempfile works.
  - With the switch off, all three files are readable again.
  - A read-only folder in Documents is readable, and a program on PATH in LOCALAPPDATA runs.
  - The person is not in `CodexSandboxUsers`, the group the deny entries name.

## Not verified
- A person's own machine: OneDrive-redirected Documents (and whether changing ACLs on OneDrive
  placeholders starts a sync), a large read-only folder (the grant's icacls pass over its tree),
  and a real Python or Node installed under AppData.
- A standard user whose sandbox an administrator set up.

## Follow-ups
- Hiding other drives' user folders (Codex refuses a drive root).
