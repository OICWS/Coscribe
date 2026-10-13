# Office evaluation, part 2, Word: eight tasks, document checks, and the baseline of today's route (shipped)

Why: part 1 measures decks and PR 1 of part 2 (#181) workbooks. Word is the third kind, and its baseline has to
exist before any Word engine work starts (#164, PR 2 of 2).

## Shipped
- `--kind docx` on `evals.run`, `evals.judge` and `evals.compare`, on the same runner, judge and comparison as
  decks and workbooks (no fork): the task folder, checker, summary columns, judge rubric and comparison columns
  are chosen by kind.
- `evals/docx/tasks/`: 8 tasks (report from notes with a costs table, one-page memo from a PDF quote, tracked-changes
  edit of a contract, letter on the user's letterhead, revenue table from a CSV, Chinese/English onboarding
  notice, handbook restructure with a table of contents, picture with a caption). `docx/make_inputs.py` rebuilds
  their inputs.
- `evals/docx_checks.py`, plain Python over the document XML, in an *accepted* view (tracked changes applied) and a
  *rejected* view: facts and numbers in no input over the accepted text; real headings in order (a bold Normal
  paragraph is not one); a TOC field; tables (rows, columns, header words, each a different table); pictures no
  wider than the text area; captions in their style directly below a picture; a redline that has tracked
  insertions and deletions and rejects back to exactly the input's text; the user's template (styles defined,
  header and footer text, text set in its styles, every original style still used); markdown typed into the text;
  the page count through LibreOffice.
- `tests/test_evals_docx.py` (89 tests) and `tests/docx_reference.py`: a good answer to every task that must pass every
  check, once with a faked render in CI and once with the pages really counted (skips without LibreOffice).
  Each check was broken on purpose (24 changes to the checks, the task loader, the runner, judge and comparison)
  and a test failed every time; five changes the first set of tests missed got their own tests.

## The baseline (route `current`, `deepseek-flash`, effort low, 3 judge rounds, off-peak, run twice)

| Task | Design | Content | Coherence | Facts | Pages | Structure checks | Numbers in no input | Tool calls | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 01-report-from-notes | 4.03 ±0.05 | 3.70 ±0.22 | 3.73 ±0.17 | 13/13 | 1 | headings yes, tables yes | 0 | 7 | 48 | 0.0112 |
| 02-memo-from-pdf | 4.17 ±0.12 | 4.27 ±0.21 | 4.27 ±0.33 | 10/10 | 1 | - | 0 | 7 | 54 | 0.0118 |
| 03-tracked-contract | 3.67 ±0.24 | 4.57 ±0.09 | 4.50 ±0.00 | 4/4 | - | headings yes, tracked yes, template yes | 0 | 16 | 100 | 0.0144 |
| 04-letter-on-template | 4.20 ±0.16 | 4.27 ±0.21 | 4.47 ±0.05 | 11/11 | 1 | template yes | 0 | 14 | 75 | 0.0133 |
| 05-table-heavy | 4.17 ±0.24 | 4.67 ±0.24 | 4.53 ±0.05 | 10/10 | 1 | tables yes | 10 | 9 | 40 | 0.0090 |
| 06-mixed-language | 3.33 ±0.24 | 3.93 ±0.09 | 4.17 ±0.24 | 9/9 | 1 | headings yes | 0 | 5 | 25 | 0.0088 |
| 07-restructure | 3.67 ±0.24 | 3.83 ±0.65 | 4.03 ±0.39 | 10/10 | - | headings yes, toc yes, tables yes, template yes | 0 | 18 | 90 | 0.0148 |
| 08-image-caption | 4.40 ±0.14 | 4.67 ±0.24 | 4.83 ±0.24 | 5/5 | 1 | images yes, captions yes | 0 | 13 | 69 | 0.0140 |
| **mean / total** | 3.95 | 4.24 | 4.32 | | | | | 89 | 501 | 0.0973 |

The second run, from the same code:

| Task | Design | Content | Coherence | Facts | Pages | Structure checks | Numbers in no input | Tool calls | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 01-report-from-notes | 4.30 ±0.14 | 4.17 ±0.33 | 4.33 ±0.24 | 13/13 | 1 | headings yes, tables yes | 0 | 4 | 34 | 0.0095 |
| 02-memo-from-pdf | 3.77 ±0.21 | 3.63 ±0.26 | 3.50 ±0.00 | 10/10 | 1 | - | 0 | 7 | 44 | 0.0105 |
| 03-tracked-contract | 4.23 ±0.21 | 4.83 ±0.24 | 4.57 ±0.09 | 4/4 | - | headings yes, tracked yes, template yes | 0 | 15 | 98 | 0.0145 |
| 04-letter-on-template | 4.00 ±0.41 | 4.67 ±0.12 | 4.60 ±0.14 | 11/11 | 1 | template yes | 0 | 20 | 132 | 0.0183 |
| 05-table-heavy | 4.37 ±0.24 | 4.70 ±0.24 | 4.57 ±0.05 | 10/10 | 1 | tables yes | 9 | 5 | 39 | 0.0091 |
| 06-mixed-language | 3.83 ±0.24 | 4.07 ±0.09 | 4.23 ±0.21 | 9/9 | 1 | headings yes | 0 | 4 | 24 | 0.0083 |
| 07-restructure | 3.00 ±0.41 | 3.17 ±0.62 | 3.67 ±0.47 | 10/10 | - | headings yes, toc yes, tables yes, template yes | 0 | 19 | 89 | 0.0146 |
| 08-image-caption | 3.90 ±0.29 | 3.93 ±0.42 | 4.33 ±0.24 | 5/5 | 1 | images yes, captions yes | 0 | 11 | 80 | 0.0137 |
| **mean / total** | 3.93 | 4.15 | 4.22 | | | | | 85 | 539 | 0.0985 |

Cost is in the units of DeepSeek's pricing page. Seconds are the sum over tasks; three ran at a time. Two runs of
one route differ by up to 0.9 points on a single task (07-restructure design 3.67 and 3.00, 08-image-caption
design 4.40 and 3.90), so only a gap larger than that on one task, or the means over eight, is a finding. "Numbers in
no input" on 05-table-heavy are the region and quarter totals the agent computed, as expected. The second run's
04-letter first read 10/11: the check wanted the word "apologise" and the letter said "I am sorry" and "apology";
the fact now accepts both, and both runs were re-checked (no model calls).

What the baseline shows:
- Every structural check passes in both runs: the agent makes real headings, tables, a TOC field, a captioned
  picture that fits, a redline that rejects back to the input, and a letter in the letterhead's own styles with
  its header and footer. The contract redline is the strongest result.
- The lowest judge scores are 07-restructure (3.67 and 3.00 design): the table of contents is a field that shows only the
  placeholder sentence "Right-click and choose Update Field" in LibreOffice and in the agent's own render, so no
  one could see that the contents list is empty (#197). The same task's Contacts table has no header row.
- 06-mixed-language scores 3.3 and 3.8 on design: little hierarchy between title and section headings and half
  a page left empty; the judge also noted a sentence added that the notes did not have in run 1.

## Not verified
- Windows, and Word itself: the documents were rendered through LibreOffice on Linux; a field or a tracked change may
  look different in Word.
- The judge shares a vendor with the model that made the documents; no Gemini round was run.
- Whether East Asian text uses a proper font in Word (the render shows no boxes; nothing checks the font names).
