# The workspace dialog is a list of rows, each opening its own page (shipped)

Why: the dialog had grown into one long scroll of sections (#926). It now shows the name, the
main folder and one row per setting with a one-line summary, the way a settings page does.

## Shipped
- The main page holds the name, the main folder and rows for Allowed folders, Sites, Secrets,
  Scripts and commands, and Environment variables. Each row shows what is set ("Any site",
  "None", the folders with "(read only)" where it applies) and opens its page; Back returns.
- Every page keeps the main page's height, so the dialog does not jump between pages.
- The editor has no grey overlay behind it.
- The e2e specs open the Sites and Secrets pages before using them.

## Not verified
- In the desktop app on Windows; checked in Chromium against a local server with a stub model
  (`rail-dialog.spec.ts`, `secrets.spec.ts`).
