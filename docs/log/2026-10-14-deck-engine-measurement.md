# Deck engine, part 2c: the engine route against today's route on the ten deck tasks (measured; the engine wins new decks)

Why: decision 0010 switches new decks to the engine only if it beats today's route on the
evaluation, cost included (issue #198, PR 3 of 4).

## Measured (2026-10-14, off-peak)
`python -m evals.run --route engine --tasks all --effort low --jobs 3`, then
`python -m evals.judge <run> --rounds 3`: the same model (`deepseek-flash`, effort low), judge,
rounds and request kind (each deck alone) as the baseline in `2026-10-13-office-eval-part2.md`.
Scores are the mean of three rounds; each cell is engine / today's route.

| Task | Design | Content | Coherence | Facts | Numbers in no input | Tool calls | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|
| 01-q3-review | 4.33 / 2.77 | 4.50 / 3.30 | 4.57 / 3.53 | 19/19 | 3 / 1 | 56 / 24 | 350 / 183 | 0.048 / 0.025 |
| 02-security-training | 4.53 / 3.40 | 4.53 / 3.73 | 4.70 / 3.57 | 10/10 | 0 / 0 | 37 / 40 | 296 / 274 | 0.036 / 0.037 |
| 03-project-proposal | 4.27 / 3.50 | 4.60 / 4.37 | 4.53 / 4.20 | 18/18 | 5 / 0 | 24 / 120 | 191 / 370 | 0.027 / 0.049 |
| 04-product-launch | 3.63 / 3.10 | 4.17 / 3.13 | 4.23 / 3.93 | 10/12 | 0 / 0 | 44 / 78 | 346 / 537 | 0.047 / 0.070 |
| 05-long-report | 4.23 / 3.20 | 4.33 / 3.67 | 4.47 / 3.97 | 22/23 | 1 / 1 | 60 / 59 | 315 / 248 | 0.050 / 0.036 |
| 06-own-template | 2.63 / 2.93 | 3.07 / 3.33 | 3.27 / 3.67 | 12/12 | 0 / 0 | 18 / 27 | 101 / 142 | 0.015 / 0.023 |
| 07-edit-deck | 3.20 / 3.40 | 4.33 / 4.47 | 3.90 / 4.17 | 5/5 | 0 / 0 | 34 / 48 | 183 / 326 | 0.026 / 0.043 |
| 08-mixed-language | 4.20 / 3.07 | 4.23 / 3.27 | 4.43 / 3.67 | 13/13 | 1 / 0 | 38 / 56 | 285 / 354 | 0.041 / 0.044 |
| 09-dense-table | 4.40 / 3.23 | 4.53 / 4.47 | 4.43 / 3.70 | 36/36 | 5 / 2 | 42 / 29 | 301 / 197 | 0.042 / 0.039 |
| 10-fifteen-pages | 4.33 / 2.50 | 4.20 / 3.17 | 4.53 / 3.00 | 21/21 | 0 / 0 | 51 / 41 | 294 / 285 | 0.046 / 0.038 |
| **mean / total** | **3.97 / 3.11** | **4.25 / 3.69** | **4.31 / 3.74** | | 15 / 4 | 404 / 522 | 2662 / 2917 | **0.379 / 0.404** |

- Every deck opens, has the asked page count, stays editable (every slide titled, its text
  listable), and has no text past an edge and no overlap, on both routes.
- On the eight new decks the engine is ahead on every score, by 1.1 on design on average.
- 06 and 07 do not use the engine: the route's instructions keep a user's template and a deck the
  user brought on today's tools, and the agent did. Their differences are run-to-run variation
  of today's route.
- Cost: 0.379 against 0.404 (dollars on DeepSeek's page, about 2.5 yuan); time 2662 s against
  2917 s. The run read 18.0M input tokens (17.3M cached) and wrote 0.38M, 0.23M of it reasoning.
  The judge cost 0.055 more; nothing was run twice.
- 09 ended with a dropped connection to the model (`peer closed connection`) after the deck was
  written and before the agent's last message; the deck was checked and judged as it was.

## What the checks flagged, read page by page
- Facts: 04's "399 元" and "50 元" are on the slides as "¥399" and "¥50"; 05 leaves out one share
  of a survey ("41%", the largest). 04 is a rewrite, 05 a real omission.
- Numbers in no input: 14 of the 15 are figures computed from the material and correct (09's
  totals and shares, 03's budget shares, 01's sums); one is a date the material does not give
  (03's "2026 年 10 月" on the cover and in the footer).
- `SKILL.md` now says: no date unless the material gives one, a figure keeps the unit the
  material writes, a breakdown keeps all its parts, and the plan checks each of the material's
  figures before pages are written.

## Not verified
- Windows.
- The guide change above was not run again here; tasks 03, 04 and 05 are run with it off-peak and
  the result is added to this PR.
- The judge is DeepSeek scoring DeepSeek's decks; it scores both routes the same way, so the
  comparison holds, not the absolute level.

## Follow-ups
- #198 part 4: new decks on the engine in the product (the route's paragraph into the
  coordinator's instructions, "PPTX Pages" a built-in skill). `coordinator.py` is an invariant
  path, so the PR gets an independent review, and the maintainer tries it on Windows first.
