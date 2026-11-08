# Every Settings row can be searched, and a test keeps it so (shipped)

Why: Settings search lists its rows by hand in `frontend/src/components/settings/searchIndex.ts`,
because a tab's rows exist only while it is open. A row added without an entry cannot be found, and
nothing said so. Seven had been missed: the Proxy section (#666) and the two Profile rows.

## Shipped
- **The missing entries:**
  - "What should Coscribe call you?" and "What best describes your work?" (Profile).
  - "Proxy". Its Address, Do not use for, User name and Password rows show only once a manual
    proxy is chosen, so they are its keywords: searching "password" finds the Proxy row, which is
    always there.
- **The guard** (`searchIndex.test.ts`) reads every `SettingRow` in the settings tabs' source:
  - A literal label must be found, or the row it is found through must be. That row is listed in
    the test for those shown only in some state.
  - A computed label (`label={...}`) must be one the test knows, together with the labels it shows;
    a new one fails until it is listed.
  - A row whose label the test cannot read fails too.
  - It fails on `main`'s index, naming the seven rows.
- Checked in the app: searching "password" offers General › Proxy, and picking it scrolls to the
  Proxy row.

## Not verified
- In the desktop app on Windows: only the browser build was used.
