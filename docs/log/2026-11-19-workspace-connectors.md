# A workspace's own connectors connect for its conversations (shipped)

Why: phase D of #926 (decision 0048). A workspace keeps its connectors in `.coscribe/mcp.json`,
as a project keeps them in Claude Code's `.mcp.json`; part 1 made the file wait for "Use them".

## Shipped
- Once the person accepted the folder, each server in its `mcp.json` connects in the background
  and its tools reach the conversations whose main folder it is, and no other. One named like a
  connector from Settings replaces that one there.
- Whoever can write the folder wrote the file, so its servers get nothing of the person's: no
  sign-in kept for a connector of the same name, no permission set in Settings for one, and an
  entry that refers to a secret from Settings is refused.
- A change to the file outside coscribe takes its connectors from the conversations before the
  next turn starts and closes them; they come back once the person accepts it again.

## Not verified
- A real stdio and HTTP server from a workspace's `mcp.json` on Windows; the test uses a fake
  connection.

## Follow-ups
- `settings.json`'s permissions and env; the side panel's "Use them" card names the connectors
  and settings, and shows a connector that failed to connect.
