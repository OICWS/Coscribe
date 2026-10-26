# 0024: Word documents are written from a spec, compiled onto a theme and checked

Status: **not adopted** (2026-10-26, by the maintainer, after the run in
`docs/assessments/2026-10-26-word-spec-gate.md`: design 3.68 against 3.76 for markdown, the gate was
4.2). It was accepted earlier the same day (answers in
`docs/assessments/2026-10-26-word-documents-from-a-spec.md`). `write_docx` stays markdown; the code
built for it (steps 1 to 4, #640 to #643) was removed. The text below is kept as the reasoning of
the time. Extends 0013 (a document style, not a
script route) and 0019 (the .docx is the artifact); changes neither.

## Context
The viewer and the editor can only draw what they have been taught, so a document written by a
script or with unusual shapes shows wrong, and teaching them has no end. `write_docx` is steady but
cannot make a cover, KPI cards, a call-out or a chart in the flow; a script can, but adds facts, costs
more, needs a Python and an approval per run (0013), and the figures of a long document can
contradict each other.

## Decision
- `write_docx`'s `content` grows from a markdown subset to markdown with a YAML head and a small set
  of components (about eight: cover, stats, callout, chart, figure, page break, signature, contents).
  No formatting field exists in it; look comes from the theme. The tool's signature is unchanged (0001);
  the grammar lives in the Word skill.
- A compiler writes it onto real Word styles, the theme being a design system from the library (0020)
  or the house style, and marks each component so it can be read back. A template's styles still win.
- A deterministic checker, no model, lints the output (direct formatting, theme overrides, spacers,
  heading order, table width), requires that the file reads back as blocks with no locked block, and
  checks that every figure is defined once (`facts`) and agrees across text, table and chart.
- For longer documents the model writes a short plan first, approved in the plan UI; short ones skip it.
- The .docx stays the only artifact; no source file is kept beside it (0019). A script is still not the
  route for writing a document (0013).

## Consequences
- The preview and the editor are exact for documents coscribe writes, by construction and by test,
  and approximate for others, which the app says.
- Ships only if the gate in the note passes: design at least 4.2 on average and above current on
  05, 06, 08, 10 and 12; checker 0 violations; figures agree; cost within 15%.
- `write_docx`'s description and the schema snapshot change once, in the last step.

## Outcome
Steps 1 to 4 were built and the gate was run on 14 tasks, blind, three rounds, against the
markdown route and the script route. The spec route was cheaper (14%) and faster (25%) than markdown
and passed every exact check, but did not raise the design score: it won where tables, mixed
languages or a design system mattered (05, 06, 10, 14) and lost on short documents that got a
cover and a contents page they did not need (09, 12, 13). The maintainer's call was to stay on
markdown. What stays from the work: Word tasks 12 to 14 and the chart check in the evaluation, and
the rendered-page findings (stat-card wrapping, a chart axis that does not start at zero, a serif
chart font, an empty contents page) as a list of what a future change must avoid. A design system
in a Word document is the one clear gain given up; if it is wanted, it is a parameter of
`write_docx`, not a grammar.
