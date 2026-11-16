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
  It runs in the desktop CI job. `scripts/browser-native.cjs` checks real popup handles,
  content and returning to the opener instead of an adjacent tab in a separate Electron process,
  also run by the Windows desktop smoke job. The native view adopts Electron's guest WebContents.
- Local browser/network/prompt/schema/documentation tests: 51 passed. Desktop build and
  transport regressions passed; `bash scripts/check.sh --fast` passed, including 450 frontend
  tests and the quality ratchet. Documentation describes the new behavior; no SAP-specific
  workflow logic is included.

## Not verified
- Real authenticated sites, including SAP, and a person using the Windows desktop app. Native
  popup and full desktop startup smoke tests passed locally under Linux/Xvfb; Windows lifecycle
  checks run in CI. The transport double alone is not evidence of native compatibility.
- The complete Python suite is not claimed green; environment onboarding already recorded
  unrelated process-reaping, renderer and simulated Codex failures.

## Follow-ups
- Run the Windows smoke and verify native download popups on real sites before release
  (`docs/plan.md`).
