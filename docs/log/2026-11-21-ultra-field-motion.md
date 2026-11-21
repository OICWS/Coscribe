# The Ultra effort animation follows Settings > Motion (shipped)

Why: the canvas animation behind the Ultra effort option only checked the
system's reduced-motion preference, so choosing Motion: Reduced in Settings
left it moving. The CSS rule that stills every other animation can't reach
frames drawn on a canvas.

## Shipped
- `frontend/src/components/UltraField.tsx` reads `data-motion` on the root,
  which `lib/appearance.ts` already sets from the setting or the system
  preference, so both still hold it.

## Not verified
- Not looked at in the running app on Windows; `npm run build` and oxlint pass.

## Follow-ups
- None.
