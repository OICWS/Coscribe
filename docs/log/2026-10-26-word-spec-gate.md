# Word spec, step 5 part 1: the gate run and what it found

Date: 2026-10-26
Area: tools

The evaluation (`office-agent/evals`) gains Word tasks 12 to 14 (cover, contents, stats, chart and
table; figures that agree across text, table and chart; a Chinese report on a design system), the
checks for charts and for a theme, `--word-skill` to run a route's skill, a design system installed
for a task that has one, and `evals/docx/routes.py`, which builds the three routes' skills so they
differ only in the new-document part. A task's script environment (hundreds of MB) is removed once
the task is checked.

The three-way run did not pass the gate: spec 3.68 for design against current 3.76 and script 4.06
(needed 4.2). The rendered pages show real defects in the compiler (stat cards that wrap, a chart
axis that does not start at zero, a serif chart font, a contents page of its own) and a skill that
does not say a short document needs no cover. `write_docx` and the Word skill are unchanged.
`docs/assessments/2026-10-26-word-spec-gate.md` has the numbers and the next step.

Not verified: the documents in Word on Windows; whether the checker's findings are acted on.
