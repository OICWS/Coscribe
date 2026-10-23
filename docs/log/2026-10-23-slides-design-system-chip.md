# The Slides chip offers the design-system library (shipped)

Why: step 3 of the Artifacts plan (decision 0020). The server side (a Slides start that names a design system) was the pull request before this one; this is the choice itself.

## Shipped
- In the new-conversation box, a **Slides** chip carries **Design system: none**. Its menu lists the person's design systems (the library of Settings > Design systems), **No design system**, and **Manage design systems…** (**Make a design system…** while the library is empty), which opens Settings on that page. The first message goes with the choice (`design_system` beside `artifact: "slides"`). Docs, Sheets and Design starts have no such choice.
- `useArtifactStart` keeps the choice with the kind and hands both to the first message once; `App` opens Settings on a given category.
- `tests/e2e/artifacts.spec.ts`: choose a system and the socket frame carries it; another kind has no choice; the menu leads to the Design systems page.

## Not verified
- With a real model: whether a deck follows the system it was given.
- The menu closes if the message box is laid out again at that moment, as it is while a new conversation's socket connects in the dev server (a dev-only double connection); the list is therefore fetched when the chip appears, not when the menu opens.
- Windows and the desktop app.

## Follow-ups
- Assets (logos and icons), the "describe it" conversation, extraction from a .pptx, the Design System kind in Artifacts, and the checker that flags colors and fonts outside the system (`docs/plan.md`).
