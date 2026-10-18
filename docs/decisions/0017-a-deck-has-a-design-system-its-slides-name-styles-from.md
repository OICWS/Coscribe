# 0017: A deck has a design system; its slides name text styles from it

Status: proposed (2026-10-18), for the maintainer to accept. Auto layout (containers that lay out
their children) is a separate decision, 0018, and is not decided here.

## Context
The Slides properties panel (mockups: Text style, Theme colours, Design System) needs named text
styles (Heading 1, Body, ...) and the deck's theme colours. A section today carries only resolved
values (`font-size:144px`, `color:#F6F3EA`), so nothing says "this is Heading 1", and changing a
style later could not reach the slides that use it. Bundled templates already carry a palette and
fonts, but only inside their .pptx.

## Decision
- **A deck's design system is one file, `design-system.json`, in its pages folder**, beside the
  pages. It holds a name, the palette (named colours, in theme order), the fonts that export
  correctly, and the text styles (name, size, weight, font, line height, letter spacing, colour).
- **Where it comes from.** A deck built on a template gets its palette and fonts from that
  template's theme; the bundled templates are the design systems that ship. Without one, a default
  set of six styles (Heading 1, Heading 3, Lead, Eyebrow, Body, Caption) with the colours the
  deck already uses. It is created when first read, and the user's edits of it are kept.
- **A section stays self-contained.** Choosing a style writes its values into the element as today
  and marks it `data-text-style="heading-1"`; a colour pick writes the hex. Nothing in a section
  refers to the file, so build, export and the model's reading are unchanged.
- **The mark is dropped when the user overrides a value the style sets** (size, weight, font,
  line height); the style menu then shows "Custom". Editing a style in the design system later
  re-applies it only to elements still marked.
- **PowerPoint gets resolved values.** The design system is not written into the .pptx theme in
  this step.
- Only options that export to PowerPoint are offered in the panel (no backdrop blur, filter,
  blend mode); effects the format can carry (shadows, layer blur) come with the Effects step.

## Consequences
- **New**: `data-text-style` is an allowed text attribute (`section_format.py`); a design-system
  reader/writer in the pptx component and a route to read it; the properties panel reads styles
  and colours from it. Existing sections need no migration: unmarked text shows "Custom".
- **Not decided here**: the Design System page of the mockup (Colors, Typography, Spacing, Corner
  radius, Shadows, Components, Assets) and writing the palette into the .pptx theme.
