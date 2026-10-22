# Desktop: flash the taskbar when coscribe needs you, keep the computer awake while it works (shipped)

Why: with the window behind others, a finished reply or an approval waits unseen, and a long
turn is cut off when the computer sleeps. Both are settings in Settings > Sessions, on by default.

## Shipped
- `main/sessionActivity.ts`: the page reports whether a turn runs (`session:set-busy`) and when
  coscribe needs the person (`session:attention`). While a turn runs, `powerSaveBlocker`
  ("prevent-app-suspension") is held; the display can still turn off. On battery power it is held
  only when "Keep awake on battery power" is on. The settings are read from `.env` each time and
  re-checked every 30 s during a turn.
- Attention flashes the taskbar button (`flashFrame`) when the window is not focused, until it is.
  A background run that failed or waits for the person flashes too (`backgroundEvents.ts`).
- `lib/sessionSignals.ts`: the page tells the shell a turn is running, and asks for attention when
  a turn ends or an approval, question or plan starts waiting; switching conversation does not count.
- Keys `COSCRIBE_FLASH_ON_ATTENTION`, `COSCRIBE_KEEP_AWAKE`, `COSCRIBE_KEEP_AWAKE_ON_BATTERY`
  (desktop-only, saved without a restart); the rows show only in the desktop app.

## Not verified
- On a real Windows machine: that the taskbar flashes and that the computer stays awake (needs
  `powercfg /requests` while a turn runs). Only `tsc` and the settings round trip were run.
- Only the open conversation reports a running turn; a turn still running in another
  conversation does not keep the computer awake.

## Follow-ups
- Report running turns from the server, so every conversation counts.
