# Who uses the 230 names of `coscribe.tools` (2026-10-28, main at 38a85eb)

What this is: item A of issue #677. `office-agent/scripts/tools_interface_usage.py` reads every
`from coscribe.tools import X` (and `tools.X` after `from coscribe import tools`) in `src/` and
`tests/` outside `coscribe.tools`, and joins each name to the module `tools/__init__.py`
re-exports it from. Rerun it: `python scripts/tools_interface_usage.py`.

`coscribe.tools.__all__` has 230 names.

| Re-exported from | Names | Used by `src` outside `tools` | Only tests | Unused |
|---|---|---|---|---|
| `bookkeeping` | 55 | 53 | 0 | 2 |
| `exec` | 42 | 37 | 0 | 5 |
| `office.pptx` | 34 | 34 | 0 | 0 |
| `office.doc` | 24 | 24 | 0 | 0 |
| `skill_catalog` | 13 | 13 | 0 | 0 |
| `office.docx` | 11 | 11 | 0 | 0 |
| `skills` | 9 | 9 | 0 | 0 |
| `connector_permissions` | 6 | 6 | 0 | 0 |
| `web` | 6 | 6 | 0 | 0 |
| `mcp` | 5 | 5 | 0 | 0 |
| `design_systems` | 4 | 4 | 0 | 0 |
| `pptx_templates` | 4 | 2 | 0 | 2 |
| `libreoffice_install` | 4 | 4 | 0 | 0 |
| `libreoffice` | 3 | 1 | 1 | 1 |
| `pdf_pages` | 2 | 2 | 0 | 0 |
| `office.document_tools` | 2 | 2 | 0 | 0 |
| `office.xlsx` | 2 | 2 | 0 | 0 |
| `_thumbnail` | 1 | 1 | 0 | 0 |
| `_workspace` | 1 | 1 | 0 | 0 |
| `convert` | 1 | 1 | 0 | 0 |
| `files` | 1 | 1 | 0 | 0 |

## Names by the components that use them

| Used by | Count |
|---|---|
| web | 121 |
| coordinator | 26 |
| conversation | 21 |
| runtime_lg | 9 |
| conversation, web | 8 |
| conversation, runtime_lg | 6 |
| conversation, runtime_lg, web | 4 |
| conversation, coordinator, web | 4 |
| code_runtime | 4 |
| runtime_lg, web | 4 |
| cli, conversation | 3 |
| cli, web | 2 |
| workflows | 1 |
| runtime_lg, workflows | 1 |
| cli, conversation, web | 1 |
| cli, conversation, coordinator, runtime_lg, web | 1 |
| conversation, coordinator | 1 |
| coordinator, web | 1 |
| code_runtime, conversation, web | 1 |

## Used by no module of `src` outside `tools`: 11

Unused anywhere (10): `fallbacks_for_platform`, `UnisolatedConversations`, `working_interpreters`, `MessagingError`, `HandOff`, `RunningCommand`, `ScheduleRule`, `TemplateInfo`, `LibreOfficeStatus`, `load_builtin_templates`

Used only by tests (1): `find_libreoffice`


## What it shows
- 176 of the 230 names (bookkeeping 55, exec 42, pptx 34, doc 24, docx 11, web 6, xlsx 2,
  document_tools 2) are already the public names of a sub-component that `tools/__init__.py`
  re-exports. The other 54 come from loose modules (`skill_catalog` 13, `skills` 9,
  `connector_permissions` 6, `mcp` 5 and so on).
- `web` alone is the only user of 121 names; `conversation` and `coordinator` share most of the
  rest. No name is used by every component, so no name needs the top-level package to be
  reachable from everywhere.
- 11 names are used by no module of `src` outside `tools`: ten by nothing at all
  (`fallbacks_for_platform`, `UnisolatedConversations`, `working_interpreters`, `MessagingError`,
  `HandOff`, `RunningCommand`, `ScheduleRule`, `TemplateInfo`, `LibreOfficeStatus`,
  `load_builtin_templates`) and one only by a test (`find_libreoffice`). Dropping the ten takes
  the list to 220 with no import changed.
- The 64 modules of `src` and 30 test files that import from `coscribe.tools` are the cost of
  moving a name: an import-only change, as the issue asks for item B.

## What it means for B
- Moving a sub-component's names out of `tools.__all__` makes its users import
  `coscribe.tools.exec` and so on. `ratchet.py`'s `deep_imports` counts any import with two or
  more dots below `coscribe` as deep, so it would count that import as debt although
  `lint-imports` accepts it (the package is the entry). B has to teach the metric that a
  declared sub-component is an entry first, which changes how a baseline number is measured:
  that is the maintainer's to approve (0009).
- The order that costs least: `web` (6 names), `exec` (42, 5 unused), `bookkeeping`
  (55), then the office formats. `coordinator.py` imports from `exec`, `bookkeeping` and
  `office`, so those PRs need the independent review.

## Not verified
- Only static imports are read. A name reached through `getattr`, a string or a dynamic import
  is not seen, so the ten unused names are unused as far as the AST can tell; the PR that drops
  them runs the whole suite.
- The frontend and `docs/` are not searched.
