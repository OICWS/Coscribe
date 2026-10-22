# Settings > Sessions: background agents switch, archive inactive conversations (shipped)

Why: the Sessions category should carry the session-level switches Claude's settings have, as far
as coscribe has something behind them.

## Shipped
- Background agents (`COSCRIBE_BACKGROUND_AGENTS`, on by default, live): off, `spawn_agent_background`
  stays bound (the provider caches the tool list) and answers that it is turned off, pointing to
  `spawn_agent`, which waits for the report.
- Archive inactive conversations (`COSCRIBE_ARCHIVE_INACTIVE_DAYS`: never, 7, 30 or 90 days, live):
  applied when the sidebar lists conversations (`GET /api/threads`), so no timer runs. A conversation
  that is open in the server, working or waiting for the person is left alone. One taken out of the
  archive by hand is marked `kept` in its metadata and is not archived again for inactivity.
- Tests: `tests/test_archive_inactive.py`, a chat test for the refused background spawn.

## Not verified
- A real model choosing `spawn_agent` after the refusal.
- That a conversation with background sub-agents still running is never archived when its session
  is gone (the server restarted): their records are not looked at; only an open session is.

## Follow-ups
- "Allow bypass permissions mode": coscribe has no mode that skips every check (Auto has a
  reviewer model), so it is not built; it needs a decision on whether such a mode should exist.
