# A turn keeps running when the person opens another conversation

Date: 2026-10-26
Area: server

Opening another conversation closes the socket of the one being left, and `abandon_orphaned_turn`
then cancelled its turn, so a document being written stopped midway. A turn now writes to a relay
(`_TurnSocket` in `web/routes/ws.py`) that sends each event to whichever tab has the conversation
open at that moment, or to nobody, and the turn goes on. It is cancelled only when it is parked on
an approval or a question and no tab is left to answer (the checkpointer keeps the pending request,
as before, and a reconnect redelivers it). A turn that reaches an approval while nobody is there
parks the same way.

The reply and the steps taken meanwhile are in the history when the person comes back; events sent
while nobody watched are not replayed, so the live tool progress of that stretch is not shown.

Not verified: the desktop app on Windows, and a person coming back while the turn is still running
(the test reconnects after it finished).
