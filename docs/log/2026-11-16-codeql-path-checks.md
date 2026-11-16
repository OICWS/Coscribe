# Task store paths are checked in the form code scanning recognizes (shipped)

Why: 14 open CodeQL "Uncontrolled data used in path expression" alerts (#148, #151, #154-#168,
#173) on the scheduled-task stores and the task list. #830 already limited task ids to letters,
digits, `_` and `-`, but CodeQL does not follow a check made inside another function, so the
alerts stayed open and every new store added more.

## Shipped
- `tools/bookkeeping/_trigger_files.file_in(root, name)`: the file's absolute path, or
  ValueError when it is not inside `root` (`abspath` then `startswith`). `trigger_file` returns
  through it, so every task store does; `TaskToolkit` names its thread file through it.
- Tests in `tests/test_trigger_files.py` for names that leave the folder.
- The other four open alerts are dismissed on GitHub, not changed: #172 (SHA-256 of a 32-byte
  random webhook key, not a password), #169 (the keychain-less plaintext fallback of decision
  0040), #170 and #171 (our own validation messages on a loopback route).

## Not verified
- That CodeQL closes the 14 alerts: running CodeQL in the cloud session was not allowed, so the
  PR's code scanning result is the check.
- A real Windows machine; the backslash case runs only in the Windows CI job.
