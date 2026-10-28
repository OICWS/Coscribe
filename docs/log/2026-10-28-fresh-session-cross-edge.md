# Four fresh sessions crossed a component edge; the cards say what they missed (shipped)

Why: the 2026-10-17 samples were single-component changes. #677 item C asks for changes that cross an
edge, and item D for fixing a card that sent a session the wrong way.

## Shipped
- `docs/metrics/2026-10-28-fresh-session-cross-edge.md`: four sessions, 7 to 11 files and about 5k to 9k tokens read
  each, no wrong turn.
- Card and `CLAUDE.md` additions for what they missed: the state field and settings chains, and the tool-schema
  snapshot that is skipped on Python 3.13.

## Not verified
- Sub-agents and one run per change; see the metrics file.

## Follow-ups
- #677 item B (the split of `tools`) waits for the maintainer's choice there.
