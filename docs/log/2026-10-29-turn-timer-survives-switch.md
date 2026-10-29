# The running time under the message box survives switching conversations (shipped)

Why: the maintainer switched away from a running conversation and back. The "59s · 6.8k tokens"
line started again from 0: the page timed the turn from when it first saw it running.

## Shipped
- The server's state on connect says when the running turn started (`turn_started_at`, from the
  turn lock), so a page that opens mid-turn times it from there.
- The page remembers each conversation's turn start and token count while it stays open, so
  switching back keeps both numbers. A turn the page didn't see end is detected by the server's
  start time differing from the remembered one.

## Not verified
- In the desktop app. The token count after a page reload (not a switch) starts from the reload;
  only the time comes from the server.
