# A Slides conversation can start with a library design system: the server side (partly shipped)

Why: step 3 of the Artifacts plan (decision 0020): a deck begins with the person's design system. The chip that offers the choice is the next pull request; this is what receives it.

## Shipped
- `user_message` takes `design_system` (a library id) beside `artifact: "slides"` (`wire.py`, types regenerated). For a Slides start with a system still in the library, the first message carries it in the same bracketed note as the artifact kind: the name, the overview, the colors with their notes, the fonts, the text styles, spacing and corner radius, as one sentence that guides and does not forbid (`runtime_lg/messages.py`, never the system prompt or a tool schema). The note is stripped from the replayed history like the artifact note. A system that is gone, or an id sent with any other kind, is left out.
- The conversation keeps a copy of the system as it was then (`DesignSystemStore.choose_for_thread`), so editing or deleting it in the library later does not move the conversation's deck. When the Slides panel first reads a deck of that conversation, `design-system.json` begins as that copy (`as_deck_design_system`: the palette from the colors, the fonts and text styles, with the overview, spacing and radius kept beside them) instead of the default made from the pages; once saved it is the deck's own.
- Tests: the note's wording and its stripping, the deck seed, and a socket test of the whole path (including a library edit after the start and the two left-out cases).

## Not verified
- With a real model: whether it follows the sentence (the colors and fonts it is given).
- The chip that offers the choice is not built, so nothing sends `design_system` yet.

## Follow-ups
- The Slides chip's menu: the systems, "No design system", "Make a new design system first" and "Manage design systems" (`docs/plan.md`).
- The checker that flags colors and fonts outside the system.
