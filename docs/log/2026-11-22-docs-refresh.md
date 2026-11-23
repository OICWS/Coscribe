# The top-level docs catch up with the work merged on 11-20 to 11-22 (shipped)

Why: the recurring docs check. The living documents were checked against what merged after #1000
(installing a package from the chat, the "/" menu, `/doctor`, `/fork`, side chat, the simple
conversation view, a provider's models and the bundled model catalog, each model's effort
levels, a folder's `settings.json` env, the scratch folder's delete and ACL fixes, the `@claude`
workflow, decision 0058).

## Shipped
- `SECURITY.md`: a workspace folder's `settings.json` `env` now reaches scripts and commands;
  what it can't set (variables that load code, pick a program or route traffic) and that a
  secret placeholder in it stays as written (`conversation/workspace_folder.py` `settings_env`).
- `AGENTS.md`: the layout table names the bundled model catalog in `runtime/models/`.

## Not verified
- Nothing to run; wording checked against `conversation/workspace_folder.py` and
  `runtime/models/`.

## Follow-ups
- `ARCHITECTURE.md`, `docs/plan.md` and `office-agent/README.md` were not checked: open PR #1038
  changes them.
