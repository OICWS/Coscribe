# Making a design system by describing it (shipped, part 2 of 2)

Why: the model could already save a design system (`save_design_system`, part 1); nothing in the
app started that conversation or pointed at its result.

## Shipped
- The Design system tile on the Artifacts page asks how: **Blank form** (as before) or **Describe
  it**, which starts a conversation with a "Design system" chip and the prompt "Describe the brand
  or the look you want…". The first message carries the `design-system` note.
- A turn that saved a system ends with a card (name and a one-line summary) that opens the system in
  Settings; a later save of the same id replaces the card's text, a failed save shows none
  (`lib/savedSystems.ts`, `components/chatlog/SystemCards.tsx`).
- The chat socket's `artifact` accepts `design-system` (`conversation/wire.py`, types regenerated).
- Tests: `lib/savedSystems.test.ts`, `tests/e2e/artifacts.spec.ts` (the tile's menu, both paths).

## Not verified
- A real model saving a system end to end: the e2e stub model never calls the tool, so the card is
  covered by the unit test only.
- Windows and the desktop app.

## Follow-ups
- Settings > Design systems has no "Describe it" beside "New design system" yet.
- Assets (logos) and making a system from an uploaded .pptx, on the same path.
