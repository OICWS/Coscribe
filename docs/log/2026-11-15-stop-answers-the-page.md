# Stop answers the page when no reply runs, and says "Stopping…" at any width (partly shipped)

Why: the maintainer saw Stop do nothing for a while, with no sign it was received, and "Send now"
do nothing until a second message was sent (#715).

## Shipped
- A Stop that finds no turn running gets a state event with `turn_in_flight: false`
  (`web/routes/ws.py`, `ChatSessionLG.request_stop` now says whether a turn ran). Before, a page
  that thought a reply was running got no answer at all: its Stop button stayed, and "Send now",
  which holds the person's notes until the stopped reply ends, waited forever. A second Stop now
  also clears it. `send_state`'s `on_connect` is `with_turn`, since it is no longer connect-only.
- "Stopping…" shows at any width. It was in the status beside the composer's controls, which is
  hidden below 600 px: in the desktop app with the browser panel open, Stop gave no feedback. The
  Stop button also turns grey and pulses while stopping, and stays pressable.
- Measured where a turn can be when Stop arrives, with fake models in `tests/web/` (not kept;
  the existing stop tests cover each path): a tool running 5 s in a worker thread, an approval
  card, a question card, each followed by a model taking 6 s to its first token; and a message
  sent right after the stop. Each ended within 0.05 s, so none of these is the slow stop.

## Not verified
- Why Stop took a while on the maintainer's machine: not reproduced. The issue waits for an
  exported conversation; it stays open.
- Checked in headless Chromium at 520 px with the server's reply held back
  (screenshot in the PR), not in the desktop app on Windows.

## Follow-ups
- `run_interrupt_hooks` is awaited in the socket's receive loop: a slow Interrupt hook delays the
  next message, an approval included. In `docs/plan.md` if it is ever seen.
