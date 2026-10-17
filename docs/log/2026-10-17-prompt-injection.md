# Prompt injection: a threat model, tests, and a fix for the auto reviewer (shipped)

Why: #388 item 5. Text the model reads (a file, a page, a message from another conversation) must
not approve an action, switch the approval mode or lift a limit.

## Shipped
- `docs/security/prompt-injection.md`: the channels, what stops each goal, what does not.
- `tests/web/test_prompt_injection.py`: five tests (a file claiming approval, a reply that looks like
  `/auto`, an inbox message that claims pre-approval, Plan mode against a file, the auto reviewer).
  Mutating the mode-command check or removing the reviewer filter makes them fail.
- A found gap, fixed: in Auto mode the reviewer read a message from another conversation or a
  sub-agent report as the user's own words, because those turns are stored as human messages. They
  are tagged `notice` and left out of what the reviewer is shown (`conversation/session.py`,
  `conversation/approvals.py`).

## Not verified
- Against a real model: the tests script the model's replies. Whether a real model is persuaded by
  an injected file, and whether a real reviewer model is, is not measured.
- The reviewer reading injected strings inside an action's own arguments.

## Follow-ups
- Policy files inside a writable folder (see the document): a protected-paths list in the workspace
  scope. Reported to the maintainer, not filed as a public issue.
