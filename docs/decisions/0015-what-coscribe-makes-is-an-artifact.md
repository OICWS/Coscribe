# 0015: What coscribe makes is an artifact; Slides are positioned HTML sections

Status: accepted (2026-10-17, by the maintainer). Design: `docs/assessments/2026-10-17-slides-artifact.md`.

## Context
A .pptx, .docx or .xlsx written by the model can only be looked at in the app (decision 0014), not
edited there, and every change means another full tool run or opening Office. The maintainer chose
on 2026-10-17 to make every output an artifact the user views, comments on and edits in the app,
then exports with Office quality: Slides first, then Docs, Design/Dashboard, and Sheets last. The
SVG page language (0010) compiles well but cannot be edited in a browser: its text never wraps
and SVG text has no usable caret, selection or IME.

## Decision
- **An artifact is a folder in the workspace** (`<name>.slides/`: `deck.json`, `slides/<id>.html`,
  `assets/`, `comments.json`, and `source.pptx` for an import). The exported Office file sits next
  to it; when the user named an Office format it is exported on every turn that changed the deck.
- **A slide is one positioned HTML section**, 1920×1080, a closed subset of elements and inline
  styles. Every top-level element has its own box, so one element is one PowerPoint shape and the
  compiler needs no browser. Drawings inside a section stay SVG and go through the existing
  SVG → DrawingML code; charts are native charts.
- **Only what was edited can lose anything.** An imported slide that was not edited is copied from
  `source.pptx` verbatim on export; an edited one is compiled from its section (by slide first,
  later by shape).
- **The person's edit wins.** A model write to a slide changed after the model last read it is
  refused. The person's edits reach the model as a message at the start of a turn, never through
  a tool schema or the system prompt (0001). Undo covers the model's turns.
- **Slides are drawn in the app's own DOM** (a shadow root), because the validator admits no script,
  handler or remote URL. Artifacts that run their own JavaScript (Design, Dashboard) are drawn
  in a sandboxed iframe.

## Consequences
- **0010's evaluation decides the switch**: the HTML route replaces the SVG pages only if it is
  at least level with them on the deck evaluation. Until then `build_pptx_from_pages` stays.
- **Tool list**: the check/export tool replaces or extends `build_pptx_from_pages` in one
  reviewed change (0001); sections are written with the existing file tools.
- **Writes go through the backend**: the panel sends edits to a route that validates and writes
  the section, as 0014 requires of the viewers.
- **New compiler**: an HTML-subset → PPTX compiler and a .pptx → section importer are new code to own.
- **Comments stay in the app**; they are not written into the exported .pptx.
