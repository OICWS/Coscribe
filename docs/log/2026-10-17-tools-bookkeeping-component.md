# `tools.bookkeeping` is a component, and `tools` is cut (shipped)

Why: issue #348 item 1. The model's own state (task list, scheduled tasks, sub-agent and
background runs, wakes, messages, questions, memory) was eight loose modules in `tools/`.

## Shipped
- A pure move: `tasks`, `scheduled_tasks`, `subagent_tasks`, `background_tasks`, `selfwake`,
  `conversations`, `interaction` and `memory` are now `tools/bookkeeping/`, with an `__init__.py`
  (`__all__` of the 41 names `coscribe.tools` already exported), a card and a `components.toml`
  entry. `coscribe.tools` still exports the same names.
- The known upward import is renamed in `pyproject.toml`
  (`coscribe.tools.bookkeeping.scheduled_tasks -> coscribe.workflows.spec`); no new one.
- The `tools` card now describes what stays in `tools/` and points to the sub-component cards.
  With this, item 1's cut of `tools` is done: office/{docx,xlsx,pdf,pptx}, exec, web, bookkeeping.
  `deep_imports` stays 37.

## Not verified
- The full suite passes locally except `test_tool_schema_snapshot` (the same failure as on `main`
  in cloud containers, #252); the web tests ran against a stub `web/static/index.html`.
- A scheduled task and a background command were not run live; nothing ran on Windows.

## Follow-ups
- Import contracts per component (#348 item 2).
- `skills.py`, `skill_catalog.py` and `pptx_templates.py` stay in `tools/`; they can become a
  component later if the skills work grows.
