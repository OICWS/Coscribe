# The script venv on Windows is made from coscribe's own Python (shipped)

Why: issue #560. Allen chose a python-build-standalone download. A system Python can be missing,
a Store alias that only opens the Store, or installed where the scripts' container then has to
be granted read (Program Files, another user's AppData).

## Shipped
- `tools/exec/own_python.py` downloads python-build-standalone's `install_only` build into
  `<state>/python` on first need, and checks it against the SHA-256 pinned there:
  - release `20261021`, CPython 3.12.15, for x86_64, ARM64 and x86 Windows. Not 3.13: from 3.13 on
    Python resolves its own path with `GetFinalPathNameByHandleW` at start, which the container is
    denied, so every script warned "Failed to find real location" on stderr (seen on the runner);
  - the hashes were taken from the release's `SHA256SUMS`, and the x86_64 archive was downloaded
    and checked against its hash.
- The download is unpacked into a temporary folder and moved in whole, so a cut-short download
  never looks installed.
- `script_env`: the venv is made from that Python first. An interpreter chosen in
  Settings > Environment still wins, and a failed download falls back to the Pythons detected on
  this computer, with the reason in the error if none works.
- Existing script venvs are kept as they are.
- The container reads the venv's base installation (`home` in `pyvenv.cfg`), which is now under
  the state folder.
- The Windows CI job now also runs on changes to `own_python.py` and `script_env.py`. There the
  script venv is made, so it runs the real download.

## Not verified
- On a Windows machine without a system Python (CI's runner has one, but the own Python goes
  first, so the Windows job makes the venv from it).

## Follow-ups
- Moving the Python to a newer build is a change to the three constants together.
