# 0047: Browser operations follow their target tab

## Status
Accepted. Narrows [0036](0036-a-step-runs-several-lanes-at-the-same-time.md), browser scheduling only.
Issue #907.

## Context
A single conversation-wide browser queue prevented independent pages from working together.
Automation selection also competed with the page the person wanted to see. Saved workflows
could not reliably name a page created at runtime.

## Decision
- Resolve and pin each operation to its target tab before queuing. Operations on one tab
  serialize; different tabs in a conversation can execute together. User selection stays separate.
- Browser tools accept runtime ids, saved tab names and relative targets. Structured tab info
  can be saved and referenced with existing workflow value expressions.
- Parallel lanes whose browser steps specify targets may overlap. Untargeted browser lanes,
  autonomous agents and called tasks retain the lane lock because their destinations are unknown.
- Live background pages retain off-window native views. Foreground overlays control visibility;
  automation never makes a hidden native view visible. Layout updates preserve the double bounds
  workaround, while unchanged geometry and viewport metrics are not resent.
- Completed download popups can be cleaned explicitly after downloads finish. User-controlled,
  visible, active and unsuccessful-download pages are retained. No site-specific title rules.

## Consequences
Per-tab activity and explicit takeover accompany independent tabs. Workflow tests stream real
step records, including iteration paths, through the existing progress event and retain them
in their result. Form batches reuse ordinary input operations in the target tab.

Retired wording: "Lanes that may use the browser take turns", "Lanes that use the browser take turns, since there is one."
