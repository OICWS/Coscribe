# Settings show only what a person sets (shipped)

Why: Settings read as homework. It listed every tool, internal limits and file paths, and asked a
person to press Test and Save. The maintainer's rule for this pass: a setting is there only when a
person has a reason to change it, a switch does its own setting up, and a large download starts
only when the person asks. The look follows claude.ai's Settings.

## Shipped
- **Eight pages, not ten.** Tools is gone (a list to read, nothing to set). Sessions is a
  "Conversations" section of General. Workspace is "Environments": the environments with Edit and
  New (`EnvironmentsSection.tsx`, the dialog the chat's picker opens), then "Other folders".
- **Rows removed from the page; the keys still work from `.env`:** Max steps per reply, Log
  level, Model for side jobs, Port for task events, Default workspace, Skills folder, Memory file
  and the three config-file paths. The server's allowlist is unchanged.
- **Capabilities is one list of switches.** Run scripts shows a line only when the isolation check
  failed, with Retry. Run commands sets up the basic sandbox itself when it goes on; under it,
  "Command sandbox" is a menu (Basic, Full, No sandbox) with one sentence for the one picked. Full
  without an administrator's approval says so and returns to what was in use. No sandbox still
  asks its own confirmation (decision 0022). "Private folders" opens Environments; "Allowed
  sites" (desktop app) opens the browser's list. The overview table, the isolation card and the
  sandbox cards are gone.
- **Advanced**, under Capabilities: Python for scripts (Choose), Packages for scripts (Manage),
  LibreOffice and Codex. The two downloads show their size, where they are kept, and Download,
  Update or Remove; turning on "Chats can hand tasks to Code" no longer fetches anything.
- **Proxy has no Test or Save.** A mode is saved when picked, the manual fields when focus leaves
  them, and Coscribe then tries the connection and says what it reached.
- **The look:** the first heading sits level with Search at the size of the others, rows are
  parted by a light hairline, and a row's own options sit indented under it with no line between
  (`SubRows` in `SettingRow.tsx`). The nav has no "Settings" label.
- Removed with them: `ToolsTab`, `CodeTab`, `LibreOfficeCard`, `ScriptIsolationCard`,
  `CodeModuleStatus`, the cards of `CommandModes.tsx` (its hook is `useCommandSandbox.ts`).
  Two messages and the README name the pages as they are now.

## Not verified
- Anything on Windows: moving between the sandboxes, the fall back when the administrator prompt
  is declined, Retry after a failed isolation check, the Allowed sites row in the desktop app,
  downloading, updating and removing Codex and LibreOffice from the new rows. The screenshots
  were taken on Linux with those states answered by a mocked API.

## Follow-ups
- `web/webhook_listener.py` still says "pick another in Settings > Sessions" when its port is in
  use; the row is gone. It is an invariant path, so it changes with the port follow-up below.
- In `docs/plan.md`: the Artifacts and "Create and edit files" switches, no cap on steps, a port
  that moves itself, a diagnostic log to export, packages installed from the chat, models for
  code and side jobs picked without a row.
