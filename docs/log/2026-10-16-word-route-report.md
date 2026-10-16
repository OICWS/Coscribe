# Word route measured: layout, not the way of writing, is the gap (shipped)

Why: after Excel, the next office format is Word. Its eight evaluation tasks all spell out the
layout, so two open tasks were added first (#324) and the two routes were compared on all ten.

## Shipped
- `docs/assessments/2026-10-16-word-quality.md`. Two rounds of `write_docx` against a document
  written whole by one python-docx script, each document judged blind three times:
  - design 3.91 and 3.70 against 4.17 and 4.26;
  - content and coherence level;
  - every deterministic check passed except one dropped heading in the script route.
- The design gap repeats only on layout: 05 table (+0.87, +1.80), 06 mixed Chinese and English
  (+1.03, +1.53), 08 image with a caption, 10 half-year summary.
- The script route added facts the notes do not give (task 01, both rounds), cost 8–19% more
  and took about 35% longer.
- Decision record 0013 (proposed): `write_docx` gains a document style compiled onto real Word
  styles; no script route; the edit tools stay. The work is issue #325, with its gate.

## Not verified
- The documents opened in Word on Windows: the judging looked at rendered pages.

## Follow-ups
- #325: the document style for `write_docx`, measured against both rounds (in `docs/plan.md`).
