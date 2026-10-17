# tools: the built-in tools the agent can call, and the stores behind them

## Purpose
Owns every built-in tool factory (`build_*_tools`) with the risk tier it carries: files and
folders (`files.py`), Word, Excel, PowerPoint and PDF (`office/`, `presentations.py`,
`convert.py`, `pdf_pages.py`), Python and Node scripts with their folder guard and isolated
environments (`scripts.py`, `node_scripts.py`, `script_guard.py`, `script_env.py`), the web (`websearch.py`, `images.py`,
`http_request.py`, `browser.py`), the model's own bookkeeping (`tasks.py`, `skills.py`,
`memory.py`, `interaction.py`, `selfwake.py`, `scheduled_tasks.py`, `subagent_tasks.py`,
`background_tasks.py`, `conversations.py`) and the connector config and permissions (`mcp.py`,
`connector_permissions.py`). Does not own the agent loop or approvals (`runtime_lg/`), the
routes (`web/`) or the coordinator's tool list (`coordinator.py`). Word, Excel, PowerPoint and
PDF have their own cards in `office/<format>/`; read those instead of this one for them.

## Public interface
Factories: `build_file_tools`, `build_document_tools`, `build_spreadsheet_tools`,
`build_presentation_tools`, `build_convert_tools`, `build_image_tools`, `build_script_tools`,
`build_node_script_tools`, `build_background_task_tools`, `build_browser_tools`,
`build_websearch_tools`, `build_task_tools`, `build_skill_tools`, `build_interaction_tools`,
`build_selfwake_tools`, `build_scheduled_task_tools`, `build_subagent_task_tools`,
`build_conversation_tools`. Toolkits and stores: `DocumentToolkit`, `SpreadsheetToolkit`,
`BackgroundTask`, `BackgroundTaskStore`, `ScheduleRule`, `ScheduledTrigger`,
`ScheduledTriggerStore`, `ScheduledRun`, `SubAgentTask`, `SubAgentTaskStore`, `WakeRequest`,
`WakeStore`, `SignalStore`, `MessagingStore`. Connectors: `validate_mcp_config`,
`load_mcp_server_configs`, `prepare_for_connect`, `name_of`, `is_read_only`, `connector_of`,
`apply_connector_permissions`, `ConnectorPermissions`. Skills and templates: `SkillInfo`,
`SkillUploadError`, `TemplateInfo`, `load_skills`, `load_builtin_skills`, `load_builtin_templates`,
`load_pptx_templates`, `save_uploaded_skill`, `slugify_skill_name`, `format_skill_listing`,
`format_template_listing`, `NEW_DECK_INSTRUCTIONS`. Memory, questions and plans: `load_memory`,
`format_memory_section`, `QUESTION_TOOL_NAMES`, `TASK_DRAFT_TOOL_NAMES`, `PLAN_CHOICE_AUTO`,
`PLAN_CHOICE_MANUAL`, `PLAN_CHOICE_REVISE`, `edit_draft`, `format_question_answers`,
`normalize_questions`. Runs and browser: `compute_next_run_at`, `parse_run_thread_id`,
`SCHEDULED_THREAD_PREFIX`, `format_incoming`, `running_subagent`, `get_subagent_transcript`,
`stop_subagent_task`, `forget_finished_subagents`, `BROWSER_HOST`, `BROWSER_RUNS`, `page_screenshot`. Folders, skills and environments: `WorkspaceScope`, `enabled_skill_names`, `ensure_script_env`, `venv_python`. Scheduled-trigger writes: `create_trigger`, `update_trigger`, `patch_trigger`, `record_draft`. Import these from `coscribe.tools`, not a submodule.

## Depends on
`coscribe.needs_permission`, `coscribe.runtime`, `coscribe.workflows`.

## Invariants
- `tools` never imports LangChain or LangGraph (import contract); only `runtime` and above know
  the agent loop. Tool schemas come from function signatures and are fixed
  (`docs/decisions/0001-fixed-cached-tool-list.md`, `tests/test_tool_schema_snapshot.py`).
- Every tool carries a risk tier (`READ`, `WRITE_LOCAL`, `EXEC`, `EXTERNAL`) through
  `tool_metadata`; approvals read it.
- File tools are scoped to the workspace root; the folder guard in `script_guard.py` catches a
  script's mistaken writes outside the conversation's folders and is not a security boundary
  (`docs/decisions/0002-approvals-not-a-sandbox.md`).
- A secret's value never reaches the model: `http_request` substitutes it after the model's call.
- Office files are compiled from whole-page sources
  (`docs/decisions/0010-office-files-are-compiled-from-whole-page-sources.md`).

## Tests
`tests/test_*_tool.py` and `tests/test_*_tools.py` per tool, `tests/test_script_guard.py`,
`tests/test_script_env.py`, the `tests/test_*_golden.py` files and `tests/test_tool_schema_snapshot.py`.

## Verify by hand
Output opened in the real Office on Windows; a script run with no Python or Node installed;
the browser tools against a real page.

## Reviewed
2026-10-14 (first card).
