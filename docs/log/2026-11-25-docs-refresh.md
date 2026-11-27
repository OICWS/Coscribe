# The top-level docs catch up with the work merged on 11-23 to 11-25 (shipped)

Why: the recurring docs check. The living documents were checked against what merged after #1039
(the user docs site, plugins from GitHub sources, the Plugins page, built-in plugins, a plugin's
services pointed to Coscribe's connectors, export as `.zip`, files returned by connectors, East
Asian fonts in generated Word and PowerPoint files, the frontend features entered through their
index, test selection and the pull request gates).

## Shipped
- `README.md`: links the user docs; the connectors and skills bullet names plugins in the Claude
  and Codex format, GitHub sources, export, and connector files saved into the workspace.
- `ARCHITECTURE.md`: the frontend's feature folders and their `index.ts`; PPTX Pages among the
  built-in skills; plugins from a repository's `marketplace.json`, export, and a plugin's MCP
  servers named but never started.
- `CONTRIBUTING.md`: a pull request's CI runs only the tests its change can reach (decision 0059).
- `docs/start-guide.md`: the invariant-path review is checked by `independent-review`.
- `office-agent/README.md`: connector file links kept behind a reference and saved by
  `save_connector_file`; generated Word files marked in their language with one East Asian face.

## Not verified
- Nothing to run; wording checked against `conversation/connector_files.py`,
  `tools/plugin_sources.py`, `tools/office/docx/_style.py`, `scripts/ratchet.py` and
  `.github/workflows/pages.yml`.

## Follow-ups
- `docs/plan.md` and `office-agent/evals/README.md` were not checked: open PRs #1071, #1074 and
  #1078 change them.
