# Drag preview without a border; Ultra's white waves start with the sweep (shipped)

Why: the maintainer's review of the panel layout and of the Ultra effort track.

## Shipped
- `components/dock/PanelDock.tsx`: while a panel is dragged, its new place is
  a soft accent fill without the dashed blue border.
- `components/UltraField.tsx`: the white waves start running as the violet
  begins to sweep in from the right, lighting squares as they appear, instead
  of waiting for the sweep to finish.

## Not verified
- The Electron app on Windows (checked in Chromium: frames at 150, 350, 600
  and 1300 ms after choosing Ultra).
