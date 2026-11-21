# The top-level docs catch up with the work merged on 11-18 and 11-19 (shipped)

Why: the recurring docs check. The living documents were checked against what merged after #968
(the first-start workspace dialog, uploads in `.coscribe/uploads/`, a workspace's own
`settings.json` and `mcp.json`, Allowed folders per workspace, emoji reactions, the workflow
task tabs, connection-string passwords, deck records).

## Shipped
- `README.md`: the first start asks for a workspace (it no longer starts in a hidden folder);
  a workspace's own permission rules and connectors.
- `ARCHITECTURE.md`: a folder's `.coscribe/` also holds `settings.json` and `mcp.json`; the Scope
  line that said there are no multi-level permission sources now names the two there are.
- `SECURITY.md`: what a workspace folder's settings and connectors may and may not do.

## Not verified
- Nothing to run; wording checked against `conversation/workspace_permissions.py`,
  `web/workspace_connectors.py` and `FirstWorkspaceDialog.tsx`.

## Follow-ups
- `office-agent/README.md` and `docs/plan.md` were not checked: open PRs #994 and #995 change them.
