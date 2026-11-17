# Context popovers preserve the browser; form batches avoid duplicate waits (shipped)

Why: opening Context usage hid the entire native browser even beside an uncovered page.
Text fields in a form batch also waited for page stability twice after each input.

## Shipped
- Only overlapping popovers make the native view step aside. The existing captured-page
  fallback preserves its picture there; uncovered pages remain live. Settings keep precedence.
- Text fields reuse their normal input operation's settle; other control kinds still wait
  for their changes. Batch input remains ordered, event-driven and available in chat and
  saved workflows; direct DOM assignment is not substituted for typing.
- Full-app Electron smoke covers the real Context card beside the native page, overlapping
  capture/restore, and Settings. Native input tests fill six fields in one command, verify
  application input handlers received the values, and reject duplicate settles.

## Not verified
- An authenticated SAP account and interactive Windows use. Existing Windows smoke jobs
  execute both the native and full-application regression scripts.

## Follow-ups
- Confirm representative SAP forms in the maintainer's account; no site-specific behavior
  or parallel keyboard-focus assumptions were introduced.
