# 0016: New slides are written as SVG pages; a slide becomes an HTML section when it is first edited

Status: accepted (2026-10-17, by the maintainer). Supersedes the part of 0015 that has the model
write new slides as HTML sections. Measurement: `docs/log/2026-10-17-slides-sections-part-4.md`.

## Context
0015 made the positioned HTML section the slide's source, so the app can edit a slide in place, and
let it replace the SVG pages only if decks written as sections measured at least level. The
measurement had two parts:
- One task with the maintainer judging by eye: the SVG deck was preferred.
- Three tasks after the guide was improved: level on two of them. On the third, the model had
  written SVG pages anyway, so its two decks differed by run alone, about as much as the
  differences being judged.

The SVG route's design guidance comes from ppt-master, which is SVG only. HTML has no such source;
improving its guide would be trial and error.

## Decision
- **The model writes every new slide as an SVG page**, as today (0010), with the "PPTX Pages"
  guide.
- **A slide becomes a positioned HTML section when the user first edits it in the app.** It is
  converted then, and from then on it is that section: the app edits it, and the model edits it
  in that language.
- **The conversion keeps the content unchanged**: the same text, positions, sizes, colours,
  pictures, drawings, charts and tables. A test compares the two compiled slides.
- **A deck folder may hold both kinds of slide.** The build compiles each slide from its own
  source, in file-name order.
- Everything else in 0015 stands: the artifact folder, the person's edit winning, only edited
  slides regenerating, comments in the app, Slides drawn in the app's own DOM.

## Consequences
- **The section compiler, its checks, tables, charts, transitions and build-ins** (#394, #398)
  serve edited slides. The "Slides" guide and the evaluation switch (#403) stay for measuring and
  for the model's edits of a converted slide.
- **New code**: an SVG page → section converter, and mixed folders in the build.
- **Showing an unedited slide** in the app is its SVG page, drawn as an image, so nothing in it
  can run.
