# Frontend unit tests with vitest (shipped)

Why: The frontend had only Playwright specs that need a running server, so the logic that decides what the transcript shows and the chat state had no fast test. These tests protect the later split of `App.tsx` into features (issue #110, part of #105).

## Shipped
- `vitest` as a dev dependency of `office-agent/frontend` (5.0.4, whose peer range includes vite 8); `npm test` runs `vitest run`. `vitest.config.ts` limits it to `src/**/*.test.ts` because the Playwright specs in `tests/e2e` fail when vitest loads them.
- `src/lib/transcriptGrouping.test.ts` (groupTurns, groupToolRuns, groupHasPendingApproval, isFailure, isRunning, workflowTests, latestWorkflowDraft, latestWorkflowDraftId, blockedWriteOf) and `src/state/reducer.test.ts` (every reducer action that changes more than one field, plus the approval, question, plan, task-draft, steer and streaming ones). Inputs are built from the real types; no `any`.
- The test files sit under `src/`, so `tsc -b` type-checks them with the app; `vite build` never imports them, so they stay out of the bundle.
- `scripts/check.sh` runs `npm test` in the frontend part, so `--fast` runs it too. It adds about 1 second.
- Both test files were checked by breaking one branch of the source at a time: 33 breaks, each failed at least one test (list in the PR).

## Not verified
- Nothing on a real Windows machine; the tests are pure functions with no file or OS access.

## Follow-ups
- Tests for the other `frontend/src/lib` files and the components (later issues of #105).
