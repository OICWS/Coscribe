# PowerPoint: the number check knows 261.5 万 is 2.615 million (shipped)

Why: on the bilingual task (14), 25 of the 27 numbers the evaluation listed as "in no input" were
the material's own counts in other units: 261.5 万辆 written as 2.615 million, 26.7 万 as 267,000.
The build's checker uses the same comparison and told the model those numbers "must come out", so
a correct deck got a warning that invited edits: rounds that cost money, or numbers removed.

## Shipped
- Numbers are compared as written and by value. A magnitude word after a number (万, 亿, 千, 百万,
  千万, 万亿, thousand, million, billion, trillion, mn, bn, and k, m or b right after the digits)
  gives its value in ones, so 261.5 万, 2.615 million, 2.615m and 2,615,000 are one number. A
  number with no unit (a table cell under a 万辆 header) still matches as written.
- The build's checker (`engine/checker.py`) and the evaluation's invention list
  (`evals/text_checks.py`) use the same functions.
- Tests: units converted both ways, a rounded total still listed, `100km` not read as thousands.

## Checked
On the four decks kept from the side-by-side with ppt-master (tasks 13 and 14, both sides):

| deck | listed before | listed after | what is left |
|---|---|---|---|
| coscribe, 13 | 1 | 1 | 140 万亿, a rounding of 1401879 亿 |
| coscribe, 14 | 27 | 2 | 1.78 million / 178 万, the top three summed |
| ppt-master, 13 | 3 | 3 | three numbers on its last page, one a date (20260228) |
| ppt-master, 14 | 31 | 5 | 36.8%, two sums and 60k, all computed by the deck |

What is left is what the check is for: figures the deck computed or rounded, which the warning
already says are fine when they come from the sources.

## Not verified
- A model run with the change: the next deck run shows whether task 14 builds with fewer
  repair rounds.
