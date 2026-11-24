# Every frontend feature is entered through its index (shipped)

Why: #1055 made each folder of `frontend/src/components/` a component and counted 106 imports
that reached into another feature's files. The count only stopped them from growing. Follow-up
to #1051 (the 2026-11-23 assessment's point 2).

## Shipped
- An `index.ts` in each of the 11 features, listing what the rest of the app uses from it (90
  names). Every import from outside a feature now goes through it, including the two lazy
  panels (`ViewerPanel.tsx`, which still load as their own chunks: `app-design.js`,
  `app-doc.js`). `frontend_feature_imports` is 0 in `quality/baseline.json`, so a new import
  into another feature's files fails `check.sh`.
- The indexes import one another. `environment` read a `settings` constant while its module
  loaded, which broke every lazy chunk in the browser (`Cannot read properties of undefined`).
  The label is now looked up on use, and `CHECK_WORDS`, which only `settings` uses, moved from
  `environment` to `settings`.
- `src/components/featureIndexes.test.ts` loads each index first, in a fresh module graph, and
  fails on such a cycle; it failed on the first version of this change. `frontend/AGENTS.md`
  says why.

## Not verified
- The app with a backend in a browser, and on Windows. Here the built chunks were loaded in
  Chromium (all load), and `npm run build`, vitest (546 tests), oxlint and knip match `main`.
  The main bundle grew 0.7% because the bundler moved a small shared chunk into it.

## Follow-ups
- None.
