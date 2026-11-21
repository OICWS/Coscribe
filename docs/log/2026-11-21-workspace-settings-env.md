# A folder's settings.json env reaches its scripts and commands (shipped)

Why: decision 0048 reads `.coscribe/settings.json` with Claude Code's meanings; its `env` was the
part not yet applied (#926).

## Shipped
- Once the person said "Use them", the `env` of the main folder's `settings.json` is passed to
  scripts and commands (`WorkspaceFolders.accepted_env`), read at each run. A change to the file
  waits for the person again.
- Names and text only, at most 100. A `{{secret:NAME}}` in a value stays as written: secrets go
  only where the workspace gives them.
- The workspace's own environment variables win on a name clash.

## Not verified
- On Windows with a real script; checked by the tests.

## Follow-ups
- The "Use them" card should list the variable names too, once #1017 is merged.
