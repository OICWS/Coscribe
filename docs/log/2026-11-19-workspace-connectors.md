# A workspace's own connectors connect for its conversations (shipped)

Why: phase D of #926 (decision 0048). A workspace keeps its connectors in `.coscribe/mcp.json`,
as a project keeps them in Claude Code's `.mcp.json`; part 1 made the file wait for "Use them".

## Shipped
- Once the person accepted the folder, each server in its `mcp.json` connects in the background
  and its tools reach the conversations whose main folder it is, and no other. One named like a
  connector from Settings replaces that one there. Entries are read as Claude Code writes them
  (`type: http` with `url`; SSE is refused), and a local server starts in the folder.
- Whoever can write the folder wrote the file, so its servers get nothing of the person's: no
  sign-in kept for a connector of the same name, no permission set in Settings for one (every
  call asks, whatever the server says of its tools), no secret from Settings, and the proxy
  address without its user name and password.
- Before every turn, the chat's and an unattended one's (a wake, a scheduled run), the folder is
  checked: a change made outside coscribe takes its connectors from the conversation first, and
  a conversation moved to another folder gets that folder's. The file is read between two
  fingerprints, so one swapped after the check doesn't connect.
- A server that failed is tried again on a later turn after 30 s, 2 min, then 10 min. Servers
  connect side by side, and at shutdown one still connecting gets 15 s to finish and is closed.

## Not verified
- A real stdio and HTTP server from a workspace's `mcp.json` on Windows; the test uses a fake
  connection.

## Follow-ups
- `settings.json`'s permissions and env; the side panel's "Use them" card names the connectors
  and settings, and shows a connector that failed to connect.
