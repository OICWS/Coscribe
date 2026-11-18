# A password inside a connector's connection string is blanked like a secret (shipped)

Why: the independent review of #957 found that `DATABASE_URL=postgres://app:pw@db/app` passed both
the credential-name and the token-shape test, so a server that printed its URL in an error showed
the password. `main` leaked it before #957 too.

## Shipped
- `_blank_credentials` (`tools/mcp.py`) also takes the secrets written inside every env and header
  value, every argument and the hosted connector's URL, at startup and on reconnect alike:
  - a URL's `user:password` and the password alone, as written and percent-decoded; the pair is
    what blanks a password under 8 characters where the URL is echoed;
  - a token in a URL's user-name place (`https://ghp_...@github.com/...`);
  - `name=value` parts named like a credential (`Password=`, `pwd=`, `api_key=`, `sig=`, `--db-password=`)
    in an ADO.NET or libpq string, a query string or an argument, and the argument after a flag such
    as `--password` or `--api-token`.
- The host, port, path, database, a user name on its own and other options (`sslmode`,
  `authSource=admin`, `sslkey=/path`) stay readable.
- Seven tests in `tests/test_connector_secrets.py`; six failed on `main`.

## Not verified
- On Windows with a real database connector; the change is in shared code, not Windows-specific.

## Follow-ups
- A password under 8 characters is blanked only where the `user:password` pair is echoed; printed
  on its own it is too short to blank without hiding ordinary words, as for any secret.
- A scheme-less DSN (`user:pass@tcp(host)/db`) and a password in an argument after a flag that does
  not name it are not recognised.
