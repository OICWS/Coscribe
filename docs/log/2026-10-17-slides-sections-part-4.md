# Slides step 1, part 4: decks as sections against SVG pages (measured; new slides stay SVG)

Why: decision 0015 let HTML sections replace the SVG pages for new slides only if they measured at
least level (issue #392, part 4). The result is decision 0016.

## Measured (2026-10-17, off-peak, `deepseek-flash` at effort low)
- **Task 01, one run each, judged by the maintainer by eye**: the SVG deck was preferred.
  - Same facts on both.
  - The SVG deck had a caption naming each table's unit, a section label, a source and page
    footer, blocks of equal height side by side, and accent-bar cards. The sections' deck had
    none of them.
  - The guide was given those (#403).
- **Tasks 01, 04 and 09, after the guide's additions** (the 15-task run was stopped at the
  maintainer's request to save tokens):

  | Task | Facts (pages / sections) | Overlapping texts | Seconds | Dollars |
  |---|---|---|---|---|
  | 01-q3-review | 19/19 / 19/19 | 5 / 0 | 217 / 154 | 0.032 / 0.029 |
  | 04-product-launch | 12/12 / 12/12 | 7 / 4 | 246 / 313 | 0.033 / 0.047 |
  | 09-dense-table | 36/36 / 36/36 | 1 / 0 | 154 / 322 | 0.032 / 0.046 |

  - The maintainer judged 01 and 09 level.
  - On 04 the SVG deck looked better (design, colour), but the "sections" run of 04 had written
    SVG pages: the model loaded "PPTX Pages" instead of "Slides". The difference seen there is
    between two runs of the same route, as large as the differences being judged.
- Twelve tasks of the stopped run on the sections route used 24.7M tokens (nearly all cached
  input) for 0.40 dollars.
  - New-deck tasks that wrote sections: 01, 02, 03, 05, 08, 09, 10, 12, 13, 14.
  - Tasks that wrote SVG pages: 04, plus 06 (own template) and 15 (redesign), as the guide routes
    them.
  - 07 and 11 edit a deck and use neither.
- Every deck on both routes kept text overlaps the checks had reported: the model stops repairing
  after two rounds.

## Decision
New slides stay SVG pages, whose design guidance comes from ppt-master; a slide becomes a section
when the user first edits it (decision 0016). Improving the HTML guide by trial and error was the
alternative; ppt-master has no HTML route to learn from (checked on its repository: SVG only).

## Not verified
- Fifteen tasks with the blind judge: stopped, so this is a small sample.

## Follow-ups
- The SVG page → section converter, keeping content unchanged, and folders that mix the two.
- Overlaps the checks report and the model leaves after its two repair rounds.
- Each evaluation task builds its own script environment, about 260 MB; fifteen of them filled
  the cloud container's disk.
