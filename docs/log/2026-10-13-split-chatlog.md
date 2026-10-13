# ChatLog split into components/chatlog/ (shipped)

Why: `office-agent/frontend/src/components/ChatLog.tsx` was 1,166 lines holding the log, a turn, tool runs, approvals, user bubbles and their helpers (#167, part 3 of 3).

## Shipped
- `components/ChatLog.tsx` (now 275 lines) keeps its name and its two exports, `ChatLog` and `TranscriptItems`, so `App.tsx` and `BackgroundTasksPanel.tsx` are untouched.
- `components/chatlog/` holds `TurnView` (with `LogItemView`, which render each other), `ToolRuns` (a run, its calls, `ToolDetail`, `ApprovalDetail`; they nest each other, so they stay in one file and no import cycle appears), `ToolPreview`, `ApprovalPreview`, `UserMessageView` (with `SteerView`), `SummaryLabel`, and `helpers.ts`, `types.ts`, `contexts.ts`.
- Moves only. A check of the multiset of lines before and after shows only imports, `export` keywords and the relative path of the lazy `Markdown` import changed.
- `helpers.test.ts` (8 tests, vitest) for the pure helpers that had none: `previewPathOf`, `pptxOverlayTargetOf`, `inSentence`. Each assertion was checked by breaking the line it protects.
- The chat log rendered from a fixture covering every kind of item (user bubbles, a long collapsed one, steers, tool runs with a preview, a failed call and a code command, pending/approved/denied approvals, question, plan, system note, task draft, streaming reply) before and after, collapsed and expanded, is pixel-identical (five states). The read-only transcript view differs only where it differs between two runs of the same code (the running-call shimmer).
- All 15 Playwright specs of the nightly E2E list pass against the stub model on the branch, run locally.

## Not verified
- The desktop app on Windows (the maintainer looks).
- The fixture harness used for the screenshots is not committed; the stub model never calls a tool, so the live app could not show tool runs or approvals.

## Follow-ups
- None; #167 is complete with this part.
