# A new Word document gets a house style (shipped)

Why: the Word route research (`docs/assessments/2026-10-16-word-quality.md`, decision 0013)
found the design gap to a script route was layout `write_docx` could not set.

## Shipped
- Without `template_path`, `write_docx` gives a document a house style on real Word styles:
  Calibri with Microsoft YaHei for East Asian text, 4 pt after and 1.1 lines, Heading 1-3 in one
  accent colour, A4, a page number in the footer, and a "Report Table" style (a shaded bold header
  row, a bold total row when the last row starts with Total or 合计). A document that opens with
  `#` sets it in the Title style, out of a contents list; `read_docx` reads Title back as `#`.
- Each numbered list restarts at 1 (all lists shared one numbering instance, so a list under a
  new heading went on counting from the last), with or without a template.
- The Word skill says what `write_docx` lays out by itself and adds the content rules.
- Eval: a wanted heading can name several levels; task 06 takes its title as Title or Heading 1.
- Measured, ten tasks, two rounds after the fixes, judged with the current and script routes:

  | | current | script | style r1 | style r2 |
  |---|---|---|---|---|
  | design | 3.74 | 4.20 | 4.02 | 4.18 |
  | content | 4.18 | 4.31 | 4.27 | 4.32 |
  | cost, 10 tasks | 0.123 | - | 0.113 | 0.120 |

  Every check passes. The gate's design of 4.2 was missed by 0.1 (round to round the same route
  moves by 0.16); the maintainer accepted it. A first measurement, before the spacing, numbering
  and title fixes, scored 3.81 and 4.05.

## Not verified
- In Word on Windows: the table style's header and total row, the PAGE field, Microsoft YaHei
  (LibreOffice here has no YaHei, so Chinese headings render without bold).

## Follow-ups
- The open tasks' layout (09 proposal, 10 summary), the lowest design scores left.
