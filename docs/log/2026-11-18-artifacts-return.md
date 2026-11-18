# Return from Artifacts to the current conversation (shipped)

Why: the sidebar ignored clicks on the current conversation even when Artifacts was open,
leaving the person unable to return without visiting a different conversation first.

## Shipped
- Thread rows also check the current page before skipping navigation. Clicking the current
  conversation from Artifacts returns directly; clicking it within chat remains a no-op.
- Playwright and the full Electron app verified the top-right Artifacts button, sidebar return,
  retained conversation history and no replacement WebSocket connection. History/list fixtures
  supplied test data; navigation and the application were real. No model call was needed.

## Not verified
- A real Windows desktop locally; the full application check ran on Linux.

## Follow-ups
- Entering Artifacts discards unsent composer text; tracked in `docs/plan.md` separately.
