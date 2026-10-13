# web/routes/settings.py is a package, one module per resource (shipped)

Why: `settings.py` was 685 lines with one 511-line `router()`; a change to one setting meant
reading all of them (issue #145, part of #150; scale assessment section 2.2).

## Shipped
- `web/routes/settings/` replaces `settings.py`. Code moved as is, one module per resource:
  `catalog` (`/api/commands`, `/api/tools`), `config` (`/api/config` and the env-var lists),
  `code` (`/api/code*`), `secrets`, `memory`, `providers`, `environments` (script-env and
  node-env packages). `__init__.py` keeps `router(state)`, which includes the seven sub-routers,
  so `web/app.py` does not change. Largest module: `config.py`, 205 lines.
- `tests/web/test_scheduled.py`: the import line now names `settings.environments`, where
  `install_package` lives; no assertion changed.
- `quality/baseline.json`: the entries for `settings.py` are replaced by the same offenders under
  their new module names (`update_config` 16, `code`/`secrets`/`memory`/`environments` deep
  imports, unchanged counts). The `router` entries drop from 511 lines / complexity 78 to
  101 / 23 (`config`) and 144 lines (`providers`).
- `tests/web_routes.txt` and `tests/tool_schemas.txt` are unchanged.

## Not verified
- Windows: ran on Linux only.

## Follow-ups
- `connectors.py` is the second PR of #145.
