# 0047: A sandboxed command can't read the Users folder of another drive

Status: proposed (2026-11-15, issue #845). Narrows 0022, whose private folders were only the
person's own on Windows' drive.

## Context
With "Private folders" on, the command sandbox denies the person's documents, OneDrive, AppData
and credential folders (0022). Codex refuses a deny on a drive's root, so a second drive stayed
readable whole, its `Users` folder included: a profile copied there from an old computer, with
the same documents, could be read by any sandboxed command.

## Decision
- **The `Users` folder of every other fixed drive is denied too** (`D:\Users`, ...), as one more
  private folder: the same deny entry, ledger and release as the others. Fixed drives only:
  removable, network and optical drives are left alone, since they come and go.
- **Not the drive that holds the person's own profile.** Its private folders are already
  denied one by one; denying its `Users` whole would hide their tools' settings (`.gitconfig`,
  caches) that 0022 keeps readable.
- **The rest of another drive stays readable**, as do `C:\Users\Public`, ProgramData and
  Windows' own folders. Settings › Capabilities says so.

## Consequences
- A sandboxed command whose environment's network is Full is still approved by the person:
  what stays readable is still enough to send out.
- A folder an environment was given inside another drive's `Users` is not denied, and a command
  whose own folder is there gets the folders beside its way down denied instead, as 0022 does
  for a private folder holding it.
- Not verified on a real Windows machine with a second drive.

Retired wording: "other drives stay readable", "still reads other drives and Windows' own folders"
