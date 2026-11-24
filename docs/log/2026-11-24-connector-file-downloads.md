# Save files returned by connectors in chat (shipped)

Canva can return a temporary URL for a PDF that the browser renders inline before any download
starts. Saving the bytes directly preserves the original file, including its text layer.

## Shipped

- A chat turns a recognized MCP file link into a temporary reference. Coscribe checks the
  workspace's network rules for each redirect and streams the original bytes to its downloads
  folder. A completed file appears in Outputs and above the message box. Failed transfers clear
  their partial files. Existing files keep their contents and names.
- A connector timeout or connection failure tells the model to check the outcome of a possible
  write before repeating it. A connector that returns an application error stays connected.
- Windows CI found a file replacement error in spreadsheet recalculation. Recalculation now
  leaves a workbook alone when it has no values to write. Formula cache writes use the shared
  atomic writer with a bounded retry for temporary Windows file locks.

## Not verified

- A private Canva export using a signed-in account or the Windows desktop. The tests supply
  simulated connector replies and exercise the real chat, activity and download routes.

## Follow-ups

- Serialize manual Retry and automatic reconnect. Check proxy-only deployments, MCP resources
  without direct links and file delivery in fixed workflow steps.
