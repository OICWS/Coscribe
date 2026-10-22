# Settings: the code module moves under Capabilities (shipped)

Why: the code module's settings sat in a "Code" category of their own; the settings
are being grouped the way Claude's are (Capabilities, then Sessions).

## Shipped
- `SettingsModal.tsx`: the `code` category is now `capabilities` (label "Capabilities", a
  briefcase icon, placed after Providers). Its content is unchanged: code module download,
  hand-off toggle, model for code, approvals. No config key changed.
- `tests/e2e/code.spec.ts` opens Capabilities instead of Code.

## Not verified
- The Playwright spec was not run here (needs a live backend); the frontend build passes.
- A real Windows window.

## Follow-ups
- A Sessions category (prompt suggestions first) in the next PR.
