# Environment variables are edited as .env text (shipped)

Why: adding variables one row at a time was slow; the page is now one text box in .env format.

## Shipped
- `environment/envText.ts`: parser and formatter (KEY=value per line, `#` comments, `export`, inline
  comments, single- and double-quoted values that may span lines). Errors name the line; the server's
  own limits (name pattern, 100 variables, 4096 characters) are checked up front.
- `VariablesPage` is a monospace textarea with the example as placeholder; saved variables are
  filled back as text, quoting only what needs it. The summary row counts parsed variables.
- Vitest for the parser and its round trip; the two e2e specs that used the rows now type text.

## Not verified
- The e2e specs themselves were not run (they need a live model backend); the dialog was driven by
  hand in light and dark against a real `coscribe-web` on Linux.

## Follow-ups
- none
