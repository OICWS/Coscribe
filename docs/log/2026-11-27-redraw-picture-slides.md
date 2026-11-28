# Redrawing a picture as an editable slide (shipped)

Why: on the OfficeVal dev tasks (#1078), turning a picture into an editable slide lost the most
points. The converter itself makes native arrowheads, dashed lines and elbows; the agent drew
around it:
- arrows as a line plus a separate triangle;
- elbows as several lines;
- the layout not measured from the picture;
- icons left out.

## Shipped
- The "PPTX Pages" skill has a section on redrawing a picture:
  - map the picture's frame onto the whole slide, axis by axis;
  - copy every element;
  - one element with `marker-end` per arrow;
  - `stroke-dasharray` for dashes;
  - every icon drawn;
  - no helper files left beside the deck;
  - one comparison against the picture, all fixes in one pass.

## Measured
Seven dev tasks, one run each, deepseek-flash, $0.95 in all:

| Task | Before | After |
|---|---:|---:|
| 055 | 0.19 | 0.57 |
| 056 | 0.17 | 0.45 |
| 057 | 0.20 | 0.90 |
| 049 | 0.59 | 0.74 |
| 051 | 0.23 | 0.29 |
| 052 | 0.57 | 0.50 |
| 046 | 0.63 | 0 |

- The mean of the six graded on the deck itself rose from 0.33 to 0.58.
- 046 scored 0 because the agent left an empty helper template beside its deck and the
  verifier opened that file. The skill now says to delete such files.
- 051, 057 and 052 ran on the final wording. The others ran on the first wording, which
  differed only for pictures that are not 16:9 and in the helper-file step.

## Not verified
- Single runs; a task can swing widely between runs.
- The held-out tasks are untouched.

## Follow-ups
- Fine geometry still loses points: exact cm positions and small composite icons (`docs/plan.md`).
