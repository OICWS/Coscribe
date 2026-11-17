# Form filling in one page execution (shipped)

Why: one tool call still entered each field separately. General browser automation needs
to edit a group together, without depending on a particular website.

## Shipped
- The default form fill resolves and checks all targets, then edits them in one synchronous
  page execution with one settle afterward. Text uses the browser's editing commands,
  rather than only assigning DOM values. An explicit typing mode keeps sequential input.
- Conversations, saved workflow tool calls and fill steps share the same implementation.
  Errors report partial progress rather than silently reverting to sequential input.
- Native Electron regressions verify six trusted text-input handlers run in one event-loop
  turn, including when the visible values already match. Mixed controls, multiline and
  literal content, empty values, preflight rejection and mid-batch replacement are covered.

## Not verified
- Authenticated SAP forms or other private websites. A successful readback is not proof
  that a site's server accepted its form; verify the submission result. Sites requiring
  separate keyboard interactions may need the explicit typing mode.
- A real Windows desktop locally; the native regression runs in the existing Windows CI job.

## Follow-ups
- Maintainer verification against the authenticated forms used in daily work (#934).
