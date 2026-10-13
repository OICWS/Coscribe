# Office evaluation, part 2: the blind judge, the comparison, and the baseline of today's route (shipped)

Why: part 1 (#155) measures a deck with scripts; this part adds a judge that looks at the rendered pages,
a table that sets two runs side by side, and the first numbers: the route as it ships today, on all 10
PowerPoint tasks. Every later step of the office route is compared against them (#139).

## Shipped
- `evals/judge.py`: a vision model (DeepSeek by default, `--judge gemini:<model>` optional) scores design,
  content and coherence from 1 to 5 and names the three worst defects. With several runs the decks of a
  task go into one request under labels drawn again every round; rounds are written under each task's
  `judge/`; `aggregate_scores` gives the mean and the spread over rounds.
- `evals/compare.py <runA> <runB>`: one Markdown file, a row per task, the runs side by side: judge scores,
  automatic checks, cost, time, tool calls, tokens, with totals.
- `tests/test_evals_judge_compare.py` (12 tests): labels, answer parsing (letters or full labels, scores
  outside 1 to 5 refused), the request order, retry, aggregation, the comparison tables. The judge call
  itself is not in CI.

## The baseline (route `current`, `deepseek-flash`, effort low, 3 judge rounds, off-peak)

| Task | Design | Content | Coherence | Facts | Pages | Editable | Numbers in no input | Words past the edge / overlaps | Tool calls | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01-q3-review | 2.77 ±0.21 | 3.30 ±0.22 | 3.53 ±0.05 | 19/19 | 6 | yes | 1 | 0 / 0 | 24 | 183 | 0.025 |
| 02-security-training | 3.40 ±0.29 | 3.73 ±0.38 | 3.57 ±0.25 | 10/10 | 7 | yes | 0 | 0 / 0 | 40 | 274 | 0.037 |
| 03-project-proposal | 3.50 ±0.14 | 4.37 ±0.12 | 4.20 ±0.16 | 18/18 | 8 | yes | 0 | 0 / 0 | 120 | 370 | 0.049 |
| 04-product-launch | 3.10 ±0.29 | 3.13 ±0.09 | 3.93 ±0.09 | 12/12 | 6 | yes | 0 | 0 / 0 | 78 | 537 | 0.070 |
| 05-long-report | 3.20 ±0.00 | 3.67 ±0.19 | 3.97 ±0.21 | 23/23 | 8 | yes | 1 | 0 / 0 | 59 | 248 | 0.036 |
| 06-own-template | 2.93 ±0.09 | 3.33 ±0.24 | 3.67 ±0.24 | 12/12 | 5 | yes | 0 | 0 / 0 | 27 | 142 | 0.023 |
| 07-edit-deck | 3.40 ±0.14 | 4.47 ±0.12 | 4.17 ±0.12 | 5/5 | 5 | yes | 0 | 0 / 0 | 48 | 326 | 0.043 |
| 08-mixed-language | 3.07 ±0.42 | 3.27 ±0.21 | 3.67 ±0.47 | 13/13 | 6 | yes | 0 | 0 / 0 | 56 | 354 | 0.044 |
| 09-dense-table | 3.23 ±0.21 | 4.47 ±0.05 | 3.70 ±0.22 | 36/36 | 3 | yes | 2 | 0 / 0 | 29 | 197 | 0.039 |
| 10-fifteen-pages | 2.50 ±0.00 | 3.17 ±0.24 | 3.00 ±0.00 | 21/21 | 15 | yes | 0 | 0 / 0 | 41 | 285 | 0.038 |
| **mean / total** | **3.11** | **3.69** | **3.74** | | | | | | | 2917 | 0.404 |

Cost is in the units of DeepSeek's pricing page (cache hit 0.003, cache miss 0.15, output 0.6 per million
tokens); the whole run read 20.7M input tokens (19.9M cached) and wrote 0.37M, 522 tool calls. Seconds are
the sum over tasks; three ran at a time.

How far two runs of one route differ, measured by running it a second time (the table of both is
`python -m evals.compare`): the mean design score was 3.11 and 3.15, content 3.69 and 3.66, coherence 3.74
and 3.79, but a single task moved by up to 0.9 (design of 01-q3-review 2.77 and 3.63; of 10-fifteen-pages
2.50 and 3.43), and cost per task moved by up to a factor of 2. A difference between two routes smaller than
that on one task is not a finding; the means over ten tasks are steadier.

What the baseline shows about today's route: every deck has all its facts and the right page count, none
overflows or overlaps, and every deck can be read and listed by coscribe's own tools (no deck of groups
among them yet, so #135 is not exercised). The judge puts design near 3.1 of 5, below content and
coherence, with the 15-page deck and the Q3 review lowest.

## Not verified
- Windows.
- The judge shares a vendor with the model that made the decks; no Gemini round was run (free tier, 20
  requests a day per model), so a same-vendor preference is possible and untested.
- The judge's agreement with a person was not measured here; the research behind decision 0010 reports
  0.9 for design with PPTEval's judge, not for this one.

## Follow-ups
- Run the deck engine (phase P1) through the same tasks and compare.
- Excel and Word tasks (later parts of #139).
