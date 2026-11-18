# Manual checks 4 and 5 run on the Windows runner; check 2's and 10's steps fixed (shipped)

Why: checks 4, 5 and 10 on #844 asked for things a person rarely has to hand (a machine whose only
Python is the Store alias, one with only conda, a live Codex run, three providers' keys), and
check 2's steps used a name, value and host the app refuses.

## Shipped
- `test_windows_real.py`: a stdio connector on a PATH whose only `python` is a Store-like stub
  says what to do; a conda Python off PATH, picked in Settings, starts it and loads its DLLs;
  Codex is not downloaded twice and its app-server exits once idle. `windows-more-checks.yml`
  finds the image's Miniconda or installs one off PATH, in both jobs.
- Found by scripting check 4: with only the stub on PATH a connector failed as "Connection
  closed". `prepare_for_connect` now raises a message that names Settings > Capabilities > Python
  for scripts (`tools/exec/script_env.py`, `tests/test_connector_interpreter.py`).
- `docs/manual-checks.md`: check 2 uses `check_1`, `abcd1234` and a host; 4 and 5 need nothing by
  hand; 10 asks only for the providers someone has a key for.

## Not verified
- The new Windows tests ran only as far as Linux allows here (the stub message, and Codex's
  download and idle exit with the Linux build); the Windows job runs them on this PR.
- A Codex turn with a real model; Claude and OpenAI as providers (no account).

## Follow-ups
- Check 17 still needs PowerPoint by hand.
