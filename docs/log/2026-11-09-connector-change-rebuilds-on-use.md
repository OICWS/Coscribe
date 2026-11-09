# A connector change no longer holds the server while every conversation rebuilds (shipped)

Why: adding, removing or updating a connector rebuilt the agent of every open conversation at
once, on the server's event loop, about a second each. With dozens open (late in the e2e suite,
or a long day's work) adding one connector took about 49 s, and nothing else the server does,
chat included, moved meanwhile. It also waited for any turn in progress, approvals included.
Found while #853's e2e run timed out.

## Shipped
- A connector change only hands each open conversation the new tool list. A conversation
  rebuilds its agent the first time its agent, its connector tools or its gated tools' risks are
  read (`RebuiltOnUse` in `conversation/agent_assembly.py`, `ChatSessionLG.apply_pending_tools`),
  so only the conversations used again pay, one at a time. A rebuild that fails keeps the
  previous tools, as before.
- Test: `test_a_connector_change_rebuilds_an_open_conversation_only_when_it_is_next_used` (no
  rebuild on the add; the one conversation reopened rebuilds and shows the new tool). The
  connector trigger e2e spec is back on the normal timeout.

## Not verified
- On Windows with many conversations open in the desktop app.
