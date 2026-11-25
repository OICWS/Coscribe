# Browser automation opens the panel in its own conversation

An Electron browser automation event already includes the conversation ID. The main renderer
now uses it so a late workflow event leaves the selected conversation's dock alone. Opening a
link in the app still opens the Browser in the current conversation.

The desktop smoke check sends a background workflow event to the active chat and checks the
Browser stays closed. It then sends an event for the active chat and checks the Browser opens.

## Not verified

- The Windows desktop run uses the existing smoke workflow.
