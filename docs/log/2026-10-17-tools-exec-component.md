# `tools.exec` is a component (shipped)

Why: issue #348 item 1. The scripts, their environments and the folder guard are one subsystem
that sat as five loose modules in `tools/`.

## Shipped
- A pure move: `scripts.py`, `node_scripts.py`, `script_guard.py`, `script_env.py` and
  `node_env.py` are now `tools/exec/`, with an `__init__.py` (`__all__` of the eight names other
  components use), a card and a `components.toml` entry. Only imports and path mentions changed;
  `tests/tool_schemas.txt`, `tests/web_routes.txt` and `tests/openapi.json` are untouched.
- Other `tools` modules (`mcp`, `_workspace`, `background_tasks`) import through the package where
  a name is exported. The Settings routes, `workflows.engine` and `background_tasks` still reach
  submodules for names that are not exported; they are the deep imports a later `protected`
  contract will list. `deep_imports` stays 37 (the ratchet keys were renamed, not loosened).

## Not verified
- The full suite passes locally except `test_tool_schema_snapshot`, which fails the same way on
  `main` in cloud containers (#252). The web tests need `web/static`, which a cloud container
  does not have; they ran against a stub index.html.
- Nothing was run on Windows.

## Follow-ups
- `tools.web` and the bookkeeping tools (#348 item 1).
