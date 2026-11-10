# Five small defects from the audit of 2026-11-10 (shipped)

Why: an audit of the settings, the first run and one real task (a CSV summed into a workbook and a
one-page brief, on `coscribe-web` with DeepSeek) found five things that were simply wrong.

## Shipped
- **Notifications saves.** General › Notifications showed the choice as picked and stored
  nothing: `COSCRIBE_NOTIFICATIONS` was missing from the keys `SettingsModal.tsx` loads and
  saves, so no request was sent and the row read "All" again when Settings reopened.
  `settings.spec.ts` now picks a level, reads it back from `/api/config` and reopens Settings.
- **The first-run page starts on the current models.** `web/setup_app.py` kept its own list
  (`claude-sonnet-4-5-20250929`, `gpt-4o`, `gemini-2.5-flash`); it now reads
  `config.DEFAULT_MODELS`, the list a key alone starts a person on, so there is one list.
- **"What best describes your work?" is gone from Settings.** Nothing read the answer: not the
  greeting, not the model. The server still accepts and returns `COSCRIBE_USER_ROLE`, so an
  existing `.env` line does no harm.
- **A folder's brief follows the folder's language.** The side model was told to write in English;
  it is now told to write in the language most of the names are in, and in English when they are
  mixed or unclear.
- **A Python script runs when the state folder is relative.** `venv_python` returns an absolute
  path. With the default `.coscribe/state`, every `run_python_script` under `coscribe-web`, the
  CLI and the evaluations failed with "No such file or directory:
  '.coscribe/state/script-env/bin/python'", because a script starts in its workspace folder. The
  desktop app passes an absolute `COSCRIBE_STATE_DIR` and was not affected.

## Not verified
- The desktop app on Windows: that a notification level saved here changes what the tray shows.
- The brief's language on more than one folder and one model (DeepSeek, a folder of Chinese
  names).

## Follow-ups
- The rest of the audit, in `docs/plan.md` ("Open, smaller", Audit of 2026-11-10).
