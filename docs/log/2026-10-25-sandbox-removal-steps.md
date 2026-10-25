# Removing the command sandbox says what it is doing (shipped)

Why: on a real machine, Remove showed nothing for a while before the administrator prompt. First
it gives the private folders their permissions back, and icacls walks each one.

## Shipped
- `GET /api/command-sandbox` reports the removal's step too: `release` (the private folders), then
  `uninstall` (the administrator prompt, elevated mode only), and the working mode with either.
- The sandbox's card lists those steps while it is removed, with the hint to look for the prompt.

## Not verified
- Clicked through on Windows: checked with the route tests and a build only.
