# Browser and workflow usability (shipped)

Why: browser work could cover settings, move the viewed page and serialize independent pages;
workflow tests hid their active steps and runtime tab ids were awkward in saved workflows.

## Shipped
- Sixteen tabs, independent targeted command queues, automation selection separate from user
  selection, per-tab activity and takeover. Explicitly targeted workflow lanes overlap (0047).
- Saved tab names, relative targets and structured runtime tab info reuse workflow references.
  Completed popup-download cleanup protects visible, user-controlled, active and failed pages.
- Form batches use the existing normal focus and input mechanism.
- Foreground overlays keep native views off-window during navigation. Identical bounds and
  metrics are skipped; changed bounds retain both Electron workaround calls.
- Context usage opens within the viewport, with wrapping aligned statistics. Stop retains its
  existing behavior without an automatic follow-up question.
- Draft tests retain and stream real per-step/iteration records. Their hierarchical list shows
  separate aligned type/status icons, branches, parallel activity and loop counts, with reduced
  motion and restrained active-step scrolling.

## Not verified
- A real SAP account and Windows interactive use were unavailable in the cloud environment.

## Follow-ups
- Maintainer verifies representative SAP exports and foreground settings behavior on Windows.
