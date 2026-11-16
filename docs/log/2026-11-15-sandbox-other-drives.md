# A sandboxed command can't read the Users folder of another drive (shipped)

Why: with "Private folders" on, the command sandbox hid the person's own folders, but Codex
refuses a deny on a drive's root, so a second drive stayed readable whole, its `Users` folder
included (#845). Decision 0049.

## Shipped
- `tools/exec/_private_folders.py`: `private_folders()` adds the `Users` folder of every fixed
  drive other than Windows' own (`users_on_other_drives`, the drives from `GetLogicalDrives` and
  `GetDriveTypeW`). It goes through the same deny, grant, ledger and release as the others.
  Skipped: removable, network and optical drives, and the drive holding the person's own profile,
  whose private folders are listed one by one.
- Settings › Capabilities › Private folders says another drive's `Users` folder is hidden and the
  rest of another drive stays readable. `ARCHITECTURE.md` and decision 0022 (narrowed by 0049)
  say the same.
- A sandboxed command with Full network is still approved by the person: what stays readable is
  still enough to send out.
- Test: `tests/test_command_sandbox.py` (Windows' own drive, a drive with no `Users` and the
  drive with the person's profile add nothing; another drive's `Users` is hidden).

## Not verified
- A real Windows machine with a second drive: the drive enumeration and the deny on `D:\Users`.
  Check 6 of the Windows checks (#844) covers the sandbox setup this builds on.
