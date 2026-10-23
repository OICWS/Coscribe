# A script's approval card says whether it will run isolated (shipped)

Why: issue #560, part 3c. The card for `run_python_script`, `run_node_script` and
`run_background_script` still said every script was unsandboxed, which is wrong where the
container holds a script, and gave no sign when a conversation runs scripts without it.

## Shipped
- `chatlog/ScriptIsolationNote.tsx` reads this computer's isolation check
  (`GET /api/script-isolation`, which never runs the test) and shows one of:
  - passed: the script runs isolated, with only this conversation's folders, no deletes or
    renames, and the internet only when the Network setting is Full;
  - failed (the run reached approval, so the conversation opted out of isolation) or not Windows:
    a **Not isolated** mark and what the script can reach;
  - not checked yet: the check runs before the script, which is not run if it fails.
- The code module's and the shell command's cards keep their own text.
- e2e: `approval.spec.ts` checks the mark on the Linux runner.

## Not verified
- The passed and failed texts on a real Windows machine (the runner shows the not-Windows one).

## Follow-ups
- The sweep of grants at start and at uninstall (`docs/plan.md` item 4).
