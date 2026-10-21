# Workflow permissions and one injected-code message (shipped)

Why: CodeQL (read through a CI job on 2026-10-21) listed 79 open alerts. Four are real and small.

## Shipped
- `office-agent-ci.yml`, `windows.yml` and `desktop-build.yml` declare `permissions: contents: read`; none of them writes to the repository, comments or calls `gh`, so the default token was wider than needed (`actions/missing-workflow-permissions`, 4 alerts).
- `browserCdp.ts`: the "no element" error built inside the code sent to the page no longer pastes the ref into a JavaScript string (`js/bad-code-sanitization`).

## Not verified
- The desktop shell was not run; the change is one message string.
- The other 74 alerts are not touched here: stack traces and paths are triaged in the PR that follows.

## Follow-ups
- A shared "the file must be inside the state folder" check for ids that become file names (`py/path-injection`, 30 alerts); `runtime/secret_store.py` is an invariant path and needs an independent review.
