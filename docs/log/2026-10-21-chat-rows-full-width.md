# Chat: tool rows as wide as the composer, one open-file chip per turn, a stop clears the approval card (shipped)

Why: the maintainer's testing of the packaged app.

## Shipped
- The tool-call rows and the approval card take the full width of the conversation column, as wide as
  the composer, instead of 92% of it.
- The chips that open a deck or document appear once at the end of a turn, not under every run of
  calls in it.
- Stopping a reply marks the approvals still waiting as denied at once (the server already denies
  them), so the card no longer stays until it is clicked. Send now does the same.

## Not verified
- Not run in the packaged app or against a real model.
