# Scripts read only their folders; no whole-profile switch (shipped)

Why: the last item of #560 was the read scope. A switch to let scripts read the whole user profile
would grant an ACE on every file in it (minutes the first time, taken back at uninstall); a
read-only folder in Settings > Workspace gives the same reach for a smaller grant. Decision 0021
now says so.

## Shipped
- Settings > Workspace, Other folders: the description says scripts read nothing outside these
  folders on Windows, and to add a read-only folder for a script to read it.
- `AGENTS.md`, `ARCHITECTURE.md`: Codex runs no commands, so the line that it runs them as the
  user is gone; the three folder settings are named.
- Decision 0021 and `docs/plan.md` record the choice.

## Not verified
- The settings page was not opened; the change is one description string.
