# Browser page lifecycle and download ownership (partly shipped)

Why (#904): a site's popup could become the next automation target while the tool still named its
source page. Downloads belonged to a tab, so a wait on another page could miss a completed file.

## Shipped
- Popups use Electron's native `createWindow` callback inside the existing WebContentsView
  tabs, retaining the opener and WindowProxy. During AI work they stay in the background;
  tool results report changed tabs and their source, including changes between commands.
- Selecting and closing tabs remains explicit. Closing a popup prefers its source; pages that
  close themselves are removed. A full group refuses a popup instead of replacing its source.
- Download records belong to a conversation and survive tab closure. Waiting for a download
  needs no responsive renderer. Only untouched blank popups close after successful downloads;
  login and business pages remain open. Interrupted downloads are not reported as successful.
- Individual protocol operations have bounded waits; a backend timeout cancels the matching
  request without cancelling a later step. Control messages bypass the per-conversation queue.
- `npm run test:browser` exercises the actual panel/queue code with an Electron transport double:
  navigation reuse, popup selection and close, delayed popup feedback, overflow, page destruction,
  download ownership/cleanup/isolation, renderer-independent waiting, and cancellation/timeouts.
  It runs in the desktop CI job. The Windows desktop smoke also checks real popup handles and
  returning to the opener instead of an adjacent tab.
- Local browser/network/prompt/schema/documentation tests: 51 passed. Desktop build and
  transport regressions passed; `bash scripts/check.sh --fast` passed, including 450 frontend
  tests and the quality ratchet. Documentation describes the new behavior; no SAP-specific
  workflow logic is included.

## Not verified
- The Windows desktop smoke and real authenticated sites, including SAP. This Linux task has
  not run that native smoke; a transport double is not evidence of native popup compatibility.
- The complete Python suite is not claimed green; environment onboarding already recorded
  unrelated process-reaping, renderer and simulated Codex failures.

## Follow-ups
- Run the Windows smoke and verify native download popups on real sites before release
  (`docs/plan.md`).
