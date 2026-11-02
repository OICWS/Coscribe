# Settings search no longer returns scrollIntoView's promise from an effect (shipped)

Why: the Design inspector crashed on CI's Chromium 156 with "destroy is not a function"
(fixed in #769). Newer Chromium returns a promise from `scrollIntoView`, and an effect written
as `() => el.scrollIntoView()` hands that promise to React, which calls it as the cleanup. The
settings search had the same line, so it would crash once Electron's Chromium catches up.

## Shipped
- `SettingsSearch.tsx`: the effect that scrolls to the active result now has a block body.
- `frontend/src/lib/effectReturns.test.ts` reads every source file and fails on an effect that
  returns a DOM call's value (`scrollIntoView`, `scrollTo`, `scrollBy`, `animate`,
  `requestFullscreen`, `focus`, `blur` or `play`). It fails on the old settings line.
- The other effects with an expression body return a setter's `undefined` or an unsubscribe
  function on purpose, and are left as they are.

## Not verified
- Not run in a Chromium that returns the promise: local Chromium returns `undefined`, and no
  e2e spec types into the settings search.
