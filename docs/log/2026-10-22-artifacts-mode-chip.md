# A kind from the Artifacts page starts a conversation with a chip and a prompt for it

Why: "Make something new" jumped to a new conversation with a few words typed into the box, which read as abrupt and told coscribe nothing. The maintainer asked for the kind to be shown in the composer and to reach coscribe as an instruction. Step 1 of three (plan.md); design systems come later.

## Shipped
- Choosing Docs, Slides or Sheets opens the new conversation with a chip in the message box (Remove to drop it) and a prompt for the kind in place of the typed words ("Describe the presentation you want"). Dashboard stays "Soon".
- The first message carries `artifact` (`docs`, `slides` or `sheets`) on the chat socket (`wire.py`, types regenerated). The session puts a note in front of the message with the other turn notes: what is being made and which tools to use, in the message, never in the system prompt or a tool schema (decision 0001). `strip_mode_note` removes it from the replayed history, so the bubble shows only what the person typed.
- Tests: the note and its stripping; a socket round trip whose replay shows no note; the Artifacts spec for the chip and for the first message.

## Not verified
- Not run with a real model: whether the note makes the model use the right tool first is for the maintainer to see in use.
- Not run on Windows or in the desktop shell.

## Follow-ups
- Step 2: the design-system library (decision 0020, waiting for acceptance); step 3: the Slides chip's choice of a system.
