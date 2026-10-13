# 0010: Office files are compiled from whole-page sources; open-source code is reused as owned copies

Status: proposed (2026-10-13), for the maintainer to accept. Evidence:
`docs/assessments/2026-10-13-office-route.md`.

## Context
coscribe's decks are assembled one tool call at a time on prefab layouts. On the same content and
model, a model that writes each page as one whole SVG, compiled to native PowerPoint shapes, made
decks a blind judge rated about 2 points higher (of 5) at a similar price (about ¥0.1–0.5 a deck on
deepseek-flash). Edits through the page source were exact (a changed number propagated to totals,
growth rates and bar heights in 17 s). The best open-source implementation is MIT-licensed; its
SVG-element-to-DrawingML core (37 modules, about 24k lines) can be copied without the rest of it.

## Decision
- A new deck is produced as page sources (a documented SVG subset) plus a deck spec, compiled
  deterministically into the .pptx, checked (compile errors, bounds, overflow, contrast, facts) and
  repaired by the model before it is delivered. Changes to such a deck rewrite the affected page
  sources. Existing tools for editing, animation, transitions, templates and raw XML stay and are
  upgraded to address shapes by name inside groups.
- What can be reused is reused: a permissive licence (MIT, BSD, Apache-2.0), copied into the
  repository as our own code with its notice, as a fixed snapshot we test and update on purpose.
  Never GPL/AGPL code, never a proprietary skill's text, never a whole foreign project embedded as a
  black box. What cannot be copied that way is written here, with the other project as reference.
- Excel and Word follow the same principle (one pass over the whole artifact, deterministic
  compile, checks, source-based edits), each decided by its own measurements, PowerPoint first.

## Consequences
- An evaluation (tasks, automatic checks, blind judge, the maintainer's look on Windows) is built
  first and decides every step; a step that does not beat the current route does not ship.
- The tool list stays fixed (0001): the engine adds at most a couple of tools, in one reviewed change.
- Copied code is excluded from size metrics like the other copied code and listed with its source.
- The split of `tools/presentations.py` follows the engine/edit/motion/qa/xml/templates boundary
  and waits until the engine's first version exists.
