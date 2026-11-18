# A password inside a connector's connection string is blanked like a secret (shipped)

Why: the independent review of #957 found that `DATABASE_URL=postgres://app:pw@db/app` passed both
the credential-name and the token-shape test, so a server that printed its URL in an error showed
the password. `main` leaked it before #957 too.

## Shipped
- `_blank_credentials` (`tools/mcp.py`) also takes the secrets written inside every env and header
  value, every argument and the hosted connector's URL, at startup and on reconnect alike:
  - a URL's `user:password` and the password alone, as written and percent-decoded; the pair (with
    the scheme when the pair is under 8 characters) is what blanks a short password where the URL
    is echoed. Each URL of a comma-separated list counts, and a password holding a raw `/` too. The
    URL is parsed by hand, so a broken one (`http://[fe80::1`) is skipped instead of failing every
    connector's start;
  - a token in a URL's user-name place (`https://ghp_...@github.com/...`);
  - `name=value` parts named like a credential (`Password=`, `pwd=`, `api_key=`, `sig=`, `--db-password=`)
    in an ADO.NET, ODBC or libpq string, a query string or an argument, and the argument after a flag
    such as `--password` or `--api-token`. An ADO.NET value runs to the semicolon, so
    `Password=my secret pw;` and a braced `Pwd={a;b}` are blanked whole.
- The host, port, path, database, a user name on its own and other options (`sslmode`,
  `authSource=admin`, `--sort-key=created_at`) stay readable. `key` counts only alone (`?key=`) or as
  an API, access, account or shared key (Azure's `AccountKey=`); a name ending in `file`, `path`,
  `dir` and the like is skipped, and a value shaped like a file path is never blanked, so
  `--ssl-key /etc/ssl/client.key` stays.
- Eleven tests in `tests/test_connector_secrets.py`; ten fail without this change.

## Not verified
- On Windows with a real database connector; the change is in shared code, not Windows-specific.

## Follow-ups
- A password under 8 characters is blanked only where the URL is echoed; printed on its own it is too
  short to blank without hiding ordinary words, as for any secret. So is a password that starts with
  `/` or `~` in a `name=value` part, taken for a path.
- A scheme-less DSN (`user:pass@tcp(host)/db`) and a password in an argument after a flag that does
  not name it are not recognised.
