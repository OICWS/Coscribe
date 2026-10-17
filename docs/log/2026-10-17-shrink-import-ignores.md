# Ignored imports 42 lines to 8 (shipped)

Why: #402 item 6b. Each `ignore_imports` line is a deep import into a component's submodule that the
import contracts only tolerate; the list may only shrink.

## Shipped
- 34 lines removed from `components.toml` / `pyproject.toml`. Callers now import from the package:
  `runtime_lg` exports the MCP sign-in, tool-deferral, code-task and mode-note names; `tools` exports
  the connector, skill-catalog, bookkeeping-hook, script-environment, preview and PDF names;
  `tools.exec`, `tools.bookkeeping`, `tools.office.pdf` and `tools.office.pptx` export what their
  siblings used. Cards are updated to match `__all__`.
- `tools/presentations.py` stays as a shim, now over the `tools.office.pptx` package, which exports
  `PresentationToolkit` and `build_legacy_presentation_tools`; its two deep imports are gone.
- `web.app -> cli` (an upward import): `.env` lookup and loading moved to
  `runtime/dotenv_file.py` (`dotenv_path`, `app_data_dir`, `prepare_env`); `_load_settings_or_none`
  now lives in `web/app.py`. Behaviour is unchanged.
- `quality/baseline.json`: `deep_imports` and two long-function / file-length entries improved.

## Not verified
- The desktop sidecar's first-run path (`.env` in the app-data directory) on a Windows machine; the
  unit tests in `tests/test_setup_app.py` cover it on Linux.

## Follow-ups
- Remaining (4 imports, 8 lines because the layer and protected contracts list some twice): `tools.bookkeeping.scheduled_tasks -> workflows.spec` (needs the workflow
  validator passed in or a lower-layer spec), and four cross-format imports around
  `pptx.engine.{checker,build,native}` and `pdf.text` (the engine is off limits for this batch).
