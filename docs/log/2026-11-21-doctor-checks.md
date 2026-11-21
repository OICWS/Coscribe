# /doctor, part 1: the server's checks of what coscribe needs on this computer (partly shipped)

Why: issue #1003's comment proposed `/doctor`; the maintainer agreed on read-only checks shown as
a card, failures first, each with its next step, and on keeping the checks from drifting as
features are added. This part is the server side; nothing in the app calls it yet.

## Shipped
- `POST /api/doctor` (`web/routes/settings/doctor.py`): one short request to the default model
  (30 s limit), then Python for scripts, Node.js, LibreOffice, Edge or Chrome, the script
  container's last self-test (not rerun) and the command sandbox. Each answers `ok`, `problem` or
  `off` (not set up, or not on this platform), a detail, a fix and the Settings page it is on.
  POST because the model request costs a call.
- Each check calls the lookup its feature uses (`find_pythons`, `libreoffice_status`,
  `find_browser`, newly exported by `conversation`, `isolation_status`, `sandbox_status`); Node's
  repeats `node_env`'s two-line PATH test rather than widen `tools.exec`. A check that raises
  shows as its own problem; the others still answer.
- Keeping it current: `docs/doc-map.toml` lists `doctor.py` against those lookups' modules, so a
  pull request changing one is asked about it; the web card says a new dependency gets a check;
  `tests/web/test_settings.py` runs every check on the machine it runs on, Windows included.

## Not verified
- The checks on Windows by hand (the Windows CI job runs the test); the model check against a
  real provider (tested with a fake model and a refusing one).

## Follow-ups
- Part 2: `/doctor` in the app, as a card; after #1005 (the "/" menu) is merged.
