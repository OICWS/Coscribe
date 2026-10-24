# Sandboxed commands can't read the person's private folders (shipped)

Why: Codex's sandbox setup lets its users read every folder of the person's profile, so a
sandboxed command could read Documents, Desktop, Downloads and AppData (#601, part of #588).

## Shipped
- A new Settings › Capabilities switch, "Hide your private folders from commands", on by default:
  `commands_hide_private_folders`.
- While it is on, the permission profile denies Documents, Desktop, Downloads, Pictures, Videos,
  Music, OneDrive and AppData. The paths come from the known-folder API, so a redirected folder
  is found. Codex itself applies and keeps the deny-read entries (`tools/exec/_private_folders.py`).
- A folder the environment was given is never denied.
- coscribe grants read, once and kept in a ledger, on the read-only folders, the batch files and
  the PATH folders that lie inside a denied one.
- A command has its own TEMP/TMP in the state folder.
- Turning the switch off, or removing the sandbox, removes the ledger's grants and the deny entries.
- Decision 0022 updated: what is hidden, and that other drives and Windows' folders stay
  readable. An online sandboxed command still goes to the person.
- Real-Windows check (`test_windows_real.py`):
  - A command in a Documents workspace can't read a file beside it, on the Desktop or in
    Roaming, and Python's tempfile works.
  - With the switch off, all three files are readable again.

## Not verified
- A person's own machine: OneDrive-redirected Documents, a large read-only folder (the grant's
  icacls pass over its tree), and Python or Node installed under AppData and found on PATH.
- A standard user whose sandbox an administrator set up.

## Follow-ups
- Hiding other drives' user folders (Codex refuses a drive root).
