# A connection-string password that starts with `/` or `~` is blanked (shipped)

Why: #967 skipped any `name=value` credential that looked like a file path, and counted a leading
`/` or `~` as one. A base64 key starts with `/` about one time in 64 (Azure's `AccountKey=`), and a
password may start with either, so those were echoed unblanked. Left open in #967's follow-ups.

## Shipped
- `_PATH_SHAPED` in `tools/mcp.py` now matches only shapes base64 cannot take: a drive
  (`C:\...`), a UNC share and a relative path (`./`, `../`). A credential-named value starting with
  `/` or `~` is blanked like any other.
- `--ssl-key /etc/...` and `--password-file /run/...` stay readable, as before: their names are not
  credentials (`key` alone counts only as `?key=` or an API, access, account or shared key; a name
  ending in `file` points at a credential, not at one).
- Two tests in `tests/test_connector_secrets.py`; the one for `/` and `~` fails on `main`.

## Not verified
- On Windows with a real connector; the change is in shared code, not Windows-specific.

## Follow-ups
- A Unix path given under a credential name (`password=/run/secrets/db`) is now blanked from tool
  results. That is the safe direction, and such a setting is rare.
