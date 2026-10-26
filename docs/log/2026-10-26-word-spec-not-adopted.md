# Word spec: not adopted, and the code removed

Date: 2026-10-26
Area: tools

The spec route for Word (decision 0024: a head and `:::` components compiled onto a theme, then
checked) was built to step 4 and measured against markdown on 14 tasks, blind, three rounds
(`docs/assessments/2026-10-26-word-spec-gate.md`). Design 3.68 against 3.76 for markdown (the gate
was 4.2); cheaper by 14% and faster by 25%, every exact check passed, better on tables, mixed
languages and a design system, worse on short documents that got a cover and a contents page.
The maintainer chose to stay on markdown.

Removed: the spec parser, compiler, components, checker and theme in `tools/office/docx/`, the
`component` field the block reader had gained, and their tests (steps 1 to 4, #640 to #643). The
`docx/` folder is as it was before them. Decision 0024 is marked not adopted and keeps its
reasoning and the outcome.

Kept: Word evaluation tasks 12 to 14 (a report with contents, a table and a chart; figures that
agree across text, table and chart; a Chinese report), the chart check, `--word-skill`, and the
`current` and `script` routes' skills in `evals/docx/routes.py`. Tasks 12 to 14 have reference
solutions in markdown with `add_docx_chart`. The theme check, the design system installed for a
task and the spec route's skill went with the code.

Not verified: that nothing outside the tests reads the removed `component` field (searched: only
the removed code did).
