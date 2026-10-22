# 0020: Design systems are a library the user keeps; a deck gets a copy

Status: draft (2026-10-22, for the maintainer's acceptance; the five choices below were agreed in
conversation, the record is what he accepts or changes before step 2 is built). Builds on 0017 (a
deck has a design system) and 0015 (what coscribe makes is an artifact).

## Context
0017 gave each deck one `design-system.json`, made when the deck is first read, and left out the
Design System page of the mockup. Claude lets a person keep design systems and start a design with
one. coscribe wants the same: a person's brand is chosen once and used by every deck, and later by
documents.

## Decision
- **A design system lives in the app, per user, not in a workspace**: one folder per system in the
  app's data directory with `system.json` and its assets. Slides and, later, Docs read from this one store.
- **A deck gets a copy.** A Slides conversation started with a system chosen copies it into the deck as
  `design-system.json` (0017's file). The deck never refers back, so changing the library does not
  move a finished deck, and the deck stays self-contained.
- **What a system holds in v1**: Colors (named roles), Typography (fonts installed on the machine, and the
  named text styles; no font upload; a font may be replaced when a deck is exported elsewhere),
  Spacing, Corner radius, Assets (logos and icons, each with a note on when to use it) and an Overview
  in free text the model reads, delivered in the conversation's first message, never in a tool schema
  or the system prompt (0001). Shadows and Layouts/components come later.
- **It guides; it does not forbid.** The model is told the system; the user may choose anything. A
  checker (`check_deck`) flags colours and fonts outside the system and offers "fix to the nearest".
- **Three ways to make one**: a blank form, a "describe it" conversation of its own type ("Design
  System"), and extracting one from an existing .pptx or template. No import from GitHub or a connector.
- **Where it is managed**: Settings gets a Design systems module (list with name, updated, used by;
  "New design system" menu; a detail page with a left list of its sections). The Slides chip in
  Artifacts' new-conversation box offers the systems, "Make a new design system first" and "Manage
  design systems", which opens that module.

## Consequences
- New: a store and routes for design systems, the Settings module, an Artifacts kind "Design System"
  and its conversation type; `check_deck` learns the checker. Existing decks are untouched.
- Not decided here: shadows, layouts and components, writing a system into a .pptx theme, sharing
  systems between people, and how Docs uses a system.
- Order: (1) the new-conversation chips with their first-message instruction, no systems yet; (2) the
  library, the Settings module and the Design System conversation; (3) the Slides chip's choice of a
  system.
