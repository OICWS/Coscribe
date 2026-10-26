# Describe it in Settings > Design systems (shipped)

Why: the design note puts "Describe it" beside the blank form in both places. The Artifacts page's
Design system tile had it; Settings > Design systems had only "New design system".

## Shipped
- A **Describe it** button beside "New design system". It closes Settings and starts the same
  conversation as the tile's menu: the "Design system" chip, the prompt "Describe the brand or the
  look you want…" and the `design-system` first-message note.
- `tests/e2e/design-systems.spec.ts`: Settings closes and the chip and prompt appear.
- Ratchet accepted one line of growth in `App.tsx` and `SettingsModal.tsx`.

## Not verified
- Windows and the desktop app.

## Follow-ups
- Assets (logos, template thumbnails) kept with a design system.
