# A Files panel shows a conversation's folders, with previews and highlighted source (shipped)

Why: a person could not look into the conversation's folder from the app: a file the model wrote
or read was seen only through the Viewer (decks, Docs, designs) or in its own program. Requested
with the Claude app's Files panel as the reference.

## Shipped
- `web/routes/workspace.py`: `GET /api/threads/{id}/workspace` (the conversation's folders, the
  main one first), `.../{root}/list?path=` (one level, folders first, `.git` and Office lock files
  hidden, `node_modules`, `__pycache__`, `.venv` and `*_cache` greyed), `.../{root}/search?q=`
  (names at any depth, breadth first, at most 200 results and 20,000 entries looked at, the greyed
  folders skipped) and `.../{root}/raw/{path}` (the file inline). Read only; a path that leaves
  the folder is a 404. A page is served with `script-src 'none'`, so it is shown and never run,
  also when opened in a tab of its own; same-origin stays allowed so its pictures and styles load.
- `frontend/src/components/files/`: the panel (toolbar item "Files", pinned by default). Tabs: a
  file opened from the tree replaces the italic preview tab; a double click or the pin keeps it.
  Markdown, HTML, SVG and CSV/TSV are drawn, with "View source" beside them; code and config files
  are highlighted source only (CodeMirror 6, read only: line numbers, folding, Ctrl+F, language
  loaded by file name, loaded with the first file shown as code); pictures on a checkerboard; PDF
  in the browser's viewer; Office and binary files offer "Open in Viewer" or "Open in its app".
  Over 2 MB is not loaded. The tree hides and collapses; "Filter files..." searches by name. The
  "..." menu: Go to file (Ctrl+P while the panel is open), Show file tree, Collapse all folders,
  Word wrap (kept in the browser), then open in the Viewer, in its app, show in folder, copy the
  path, download. The panel
  reloads its folders and file after every tool call, and opens in a window of its own like the
  others (`office-agent-desktop/src/main/panelWindows.ts`).
- Dependencies: `@codemirror/{view,state,language,language-data,search,commands}`, `@lezer/highlight`.
- Tests: `tests/web/test_workspace_files.py`, `frontend/src/lib/workspaceFiles.test.ts`,
  `frontend/tests/e2e/files-panel.spec.ts` (added to the e2e job's list).

## Not verified
- The desktop app on Windows: the panel in a window of its own, a path on another drive, a large
  network folder (a search stops at 20,000 entries), and the PDF viewer inside Electron.

## Follow-ups
- None in the panel: it never edits, renames or moves a file (a person does that in their own
  program or asks the model; decision 0044). It lists a folder's `.coscribe` first.
