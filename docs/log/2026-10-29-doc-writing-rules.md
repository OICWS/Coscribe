# Docs write placeholders instead of guesses, and a report with a chart is a Doc (shipped)

Why: the maintainer asked how to raise the quality of generated Docs. Read by hand, run 1 of
`evals.doc_route` (DeepSeek flash, effort low) had:
- invented facts the person must vouch for: a resume with duties and skills nobody gave (A/B tests,
  NumPy, data engineering); minutes dated 2026-10-28 for "Wednesday";
- notes about the document ("This note covers cost... further detail can be added on request");
- the same fact in three sections (a proposal's cost, minutes' decisions again as action items);
- a letter with a `#` title.

Rerunning the briefs then showed routing is not stable either: on `main`, the Q3 report with a chart
went to `write_docx` 2 times out of 3 and the resume 3 out of 3 (Word twice, chat once). The
model finds `write_docx` through `search_tools`, and its description never said when not to use it.

## Shipped
- Docs skill, a "Writing it" section: what only the person knows is a `[placeholder]`, never a
  plausible guess, and the answer lists them; each fact once; nothing about the document itself;
  the length the brief asks for, a letter with no `#` title; a chart repeats figures of the text
  in the same order.
- `write_docx`'s description says it is for Word asked by name, a Word template or tracked changes;
  any other document is a Doc (`tests/tool_schemas.txt` regenerated on 3.11).
- `evals.doc_route` reports each Doc's length in words and the placeholders it left.

## Measured (DeepSeek flash, effort low, 2026-10-29, off-peak)
- Routing, briefs that should give a Doc: 04 report with chart 4/4 Docs (main: 1/3), 02 resume 3/4
  (main: 0/3). The Word briefs (08 by name, 09 template, 10 tracked) stayed Word 6/6. Two full runs:
  15/15 routes each.
- Read by hand: the resume has 10 to 22 placeholders and no invented duty or skill; the minutes
  leave the date as `[会议日期]` and state each decision once (91 to 140 words, against 185); the
  letter opens with the subject and greeting.
- The proposal (01) fails the fact check in some runs: it writes "three weeks" for "3 weeks".
- Cost per full run 0.14 USD against 0.06 for run 1; the main runs of 02 and 04 cost the same per
  task as the new ones, so the difference is not the skill.

## Not verified
- Other models than DeepSeek flash. Few samples per brief (2 to 4).
- Still open: the proposal invents a migration plan (three phases) the brief did not give.
