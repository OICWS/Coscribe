# A folder's settings.json env reaches its scripts and commands (shipped)

Why: decision 0048 reads `.coscribe/settings.json` with Claude Code's meanings; its `env` was the
part not yet applied (#926).

## Shipped
- Once the person said "Use them", the `env` of the main folder's `settings.json` is passed to
  scripts, commands and the code module (`WorkspaceFolders.accepted_env`), read at each run. A change to the file
  waits for the person again.
- Names and text only, at most 100, each value at most 4,096 characters. A `{{secret:NAME}}` in
  a value stays as written: secrets go only where the workspace gives them.
- A folder can't set a variable that loads code, picks a program or routes traffic
  (`PATH`, the proxies and certificates, `PYTHON*`, `NODE_*`, `LD_*`, `GIT_*`
  and every name a script takes from the system). Found in the independent review.
- The workspace's own environment variables win on a name clash, compared without case.
- The "Use them" card lists the names it would pass, under "Variables for scripts".

## Not verified
- On Windows with a real script; checked by the tests.

## Follow-ups
- Done in `docs/log/2026-11-21-sandbox-programs-path.md`: the command sandbox reads programs
  from the server's `PATH`.
