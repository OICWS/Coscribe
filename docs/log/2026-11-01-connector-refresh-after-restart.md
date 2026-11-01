# A connector whose token expired while the app was closed refreshes it instead of asking to sign in again (shipped)

Why: hosted connectors such as Hugging Face and Canva asked to be connected again after the
computer restarted. The tokens were on disk, but the MCP SDK keeps a token's expiry time and the
authorization server's metadata only in memory. A new process therefore took an expired access
token as valid, sent it, and answered the server's 401 with a new sign-in (which at startup
surfaces as `NeedsSignIn`) instead of using the saved refresh token. Where the server's token
endpoint is not `<origin>/token` (Hugging Face uses `/oauth/token`), a refresh could not have
found it either.

## Shipped
- `runtime_lg/mcp_oauth.py`: the per-connector file also keeps the access token's expiry time and
  the authorization server's public metadata (neither is a secret); the provider puts both back
  before its first request, so an expired token is refreshed at the right endpoint. A saved token
  whose expiry is unknown is refreshed once rather than trusted.
- `tests/web/test_connectors.py`: a reconnect (a new provider, as after a restart) with the
  server's access token expired refreshes without opening the browser, for a passed and for a
  missing saved expiry. The older test for an expired sign-in passed only because the first
  provider refreshed in memory before the reconnect.

## Not verified
- A real Hugging Face or Canva account on Windows. Their discovery documents were checked live:
  Hugging Face's token endpoint is `https://huggingface.co/oauth/token`, Canva's
  `https://mcp.canva.com/token`. Whether each service issues a refresh token, and how long it
  lives, was not checked; without one, a sign-in still ends when the access token does.
- A sign-in saved before this change has no metadata on file: Canva's refresh still works (its
  token endpoint is the fallback the SDK guesses), Hugging Face needs one more sign-in.

## Follow-ups
- None.
