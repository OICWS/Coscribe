# A Design started from the Artifacts page can name a library design system (shipped)

Why: a deck could start from one of the person's design systems (decision 0020), but a Design
could not, so a canvas began from colours and fonts coscribe chose.

## Shipped
- **The chip:** the Design tile's start chip in the composer has the same design-system choice as
  the Slides chip (`ArtifactChip.tsx`, `useArtifactStart.ts`).
- **The first message:** the system goes with the message.
  - On the server, `design_system_for_start` takes a Design start as well as a Slides start.
  - `artifact_note` writes the system into the first message's note. For a Design it also says
    to make the system's colors, fonts, spacing and radius the canvas's variables, and to scale
    its text sizes, which are set on a 1920-wide slide, to each artboard.
  - The Design skill already turns a named design system into the variables.
- **Tests:**
  - `tests/test_runtime_lg_messages.py`: the Design note carries the system.
  - `tests/web/test_chat_events.py`: a Design start over the socket gets it.
  - A Docs start still ignores a system.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- Not run with a real model: whether DeepSeek turns a chosen system into variables is not
  measured.
