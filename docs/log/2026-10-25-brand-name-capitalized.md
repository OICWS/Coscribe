# The product name is written "Coscribe" wherever a person reads it (shipped)

Why: the name appeared as lowercase `coscribe` in the UI, which reads as an identifier rather than
a product. Only what a person reads changes; names other things depend on stay lowercase.

## Shipped
- Frontend UI text (38 files), the page and window titles, the desktop tray, splash, dialogs and
  window titles, the connector catalog, setup page, CLI greeting, error messages and the agent's
  prompts are "Coscribe". The two READMEs' prose and titles follow.
- Electron `productName` is "Coscribe" (the installer is `Coscribe-Setup-<version>.exe`);
  `userData` is pinned to the old `coscribe` folder before the single-instance lock, so the browser
  panel's cookies and settings stay where installs have them.

## Unchanged on purpose
Package name, the `coscribe` / `coscribe-web` commands, `appId`, `COSCRIBE_*` variables, the
keychain service name, the app-data folder, the OAuth client name registered with providers, the
`[coscribe]` log and script-guard prefixes, the HTTP user agent, `(coscribe)` in copied file names,
the `"coscribe"` author value in wire data, URLs and storage keys. The connector setup text that
tells a person to name their own app "Coscribe" is a suggested name, not the registered client name.

## Not verified
- A packaged Windows build: that the installer is named as above and that an existing install keeps
  its browser-panel sign-ins after the update.

## Follow-ups
- Docs under `docs/` still use the lowercase name in prose; they were left alone to keep this change
  to what people see.
