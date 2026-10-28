# tools: the built-in tools the agent can call, and the stores behind them

## Purpose
Owns the tool layer's shared entry point and the tools that fit no smaller component: files and
folders (`files.py`), conversions (`convert.py`, `pdf_pages.py`), finding a LibreOffice (`libreoffice.py`), the connector config and
permissions (`mcp.py`, `connector_permissions.py`) and the skills and PowerPoint template
catalogs (`skills.py`, `skill_catalog.py`, `pptx_templates.py`). The rest is split by card:
Word, Excel, PowerPoint and PDF in `office/<format>/`, scripts in `exec/`, the browser, search,
HTTP and images in `web/`, the model's own state in `bookkeeping/`. Does not own the agent loop
or approvals (`runtime_lg/`), the routes (`web/`) or the coordinator's tool list (`coordinator.py`).

## Public interface
`coscribe.tools` also re-exports the public names of its sub-components (`exec`, `bookkeeping`,
`web`, `office.docx`, `office.doc`, `office.xlsx`, `office.pdf`, `office.pptx`) so older imports
keep working; read those on the sub-component's own card, and import a new name from the
sub-component. This card lists the names that belong to `tools` itself. Connectors and
permissions: `validate_mcp_config`, `load_mcp_server_configs`, `prepare_for_connect`, `name_of`,
`is_read_only`, `connector_of`, `apply_connector_permissions`, `ConnectorPermissions`, `POLICIES`,
`with_secrets`, `secret_names_used`. Skills and templates: `SkillInfo`, `SkillUploadError`,
`load_skills`, `load_builtin_skills`, `all_skills`, `enabled_skill_names`, `disabled_skill_names`,
`set_skill_enabled`, `remove_skill`, `skill_source`, `save_uploaded_skill`, `slugify_skill_name`,
`format_skill_listing`, `format_template_listing`, `load_pptx_templates`, `build_skill_tools`,
`SKILL_SAVE_CURATOR_INSTRUCTIONS`, `SKILL_SOURCE_MARKER`; the skill catalog: `SkillCatalogError`,
`load_catalog`, `get_plugin`, `plugin_file`, `install_catalog_skill`, `install_plugin`. Design
systems (decision 0020): `DesignSystemStore`, `DesignSystemError`, `as_deck_design_system`,
`build_design_system_tools`. Folders, files and conversions: `WorkspaceScope`, `build_file_tools`,
`build_convert_tools`, `pdf_page_count`, `render_pdf_page`, `render_single_page_preview`. The
Word document toolkit: `DocumentToolkit`, `build_document_tools`, `DocBlocksRefused`. The optional
LibreOffice (decision 0026): `find_libreoffice`, `libreoffice_status`, `LibreOfficeUnavailable`,
`install_libreoffice`, `libreoffice_offer`, `remove_libreoffice`. Import these from
`coscribe.tools`, not a submodule.

## Depends on
`coscribe.needs_permission`, `coscribe.runtime`, `coscribe.workflow_spec`.

## Invariants
- `tools` never imports LangChain or LangGraph (import contract); only `runtime` and above know
  the agent loop. Tool schemas come from function signatures and are fixed
  (`docs/decisions/0001-fixed-cached-tool-list.md`, `tests/test_tool_schema_snapshot.py`).
- Every tool carries a risk tier (`READ`, `WRITE_LOCAL`, `EXEC`, `EXTERNAL`) through
  `tool_metadata`; approvals read it.
- File tools are scoped to the workspace root; the folder guard in `exec/script_guard.py` is not a
  security boundary (`docs/decisions/0002-approvals-not-a-sandbox.md`).
- A secret's value never reaches the model: `web/http_request.py` substitutes it after the call.
- Office files are compiled from whole-page sources
  (`docs/decisions/0010-office-files-are-compiled-from-whole-page-sources.md`).

## Tests
`tests/test_*_tool.py` and `tests/test_*_tools.py` per tool, the `tests/test_*_golden.py` files and
`tests/test_tool_schema_snapshot.py`; each sub-component's card lists its own.

## Verify by hand
The file tools and conversions on Windows; connector permissions after a sign-in.

## Reviewed
2026-10-14 (first card).
