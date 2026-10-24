# Settings › Capabilities: scripts, commands and the Code module in one place (shipped)

Why: what coscribe may run was set in three places (Settings > Environment, each environment's
Scripts page, Settings > Code), and commands in cmd or PowerShell, which run outside the
isolation, had no switch at all. Step 2 of 4 of #588: Capabilities decides whether something can
run, an environment where and what it reaches, the mode whether you are asked.

## Shipped
- `tools/exec/capabilities.py`: `state_dir/capabilities.json`, scripts on and commands off by
  default. `require_capability` refuses at call time (the tool list stays fixed, since the
  provider caches it) with a message that points to Settings › Capabilities. Python and Node
  scripts, background scripts and `run_background_command` check it.
- `GET /api/capabilities`, `PUT /api/capabilities/{name}`; each change is an audit entry
  (`capability_<name>`).
- Settings › Capabilities: Scripts (switch, the isolation check with Test again, the Python
  picker, Python and Node packages), Commands (switch, a risk confirmation before it turns on),
  the Code module settings, and the built-in tools listed with no switch. The Environment tab is
  gone; an environment's Scripts page keeps only "run without isolation" where the check failed.

## Not verified
- On Windows: the new page and the commands confirmation were not clicked through on a Windows
  machine; the e2e spec `capabilities.spec.ts` runs in CI only.

## Follow-ups
- #588 steps 3 (named environments, the picker, scheduled tasks) and 4 (the command sandbox).
