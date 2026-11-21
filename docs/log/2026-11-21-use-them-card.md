# The "Use them" card names what the folder would change (shipped)

Why: a folder's `.coscribe` settings and connectors wait for the person's "Use them" (#926). The
card used to say only that there were settings, so the person agreed without seeing them.

## Shipped
- The thread's activity sends a folder's permission rules, grouped as allow, ask and deny, with
  its notes, skills and connectors (`WorkspacePermissions.listed`).
- The card has a title, then one group per kind: Skills, Connectors, Runs without asking, Always
  asks, Never runs. Each rule shows as its own chip. "Use them" is the primary button.

## Not verified
- In the desktop app on Windows; checked in Chromium against a local server with a stub model.
