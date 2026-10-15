# PowerPoint: speaker notes, and the first side-by-side with ppt-master's own decks (shipped)

Why: ppt-master writes speaker notes for every page and the deck engine wrote none; and whether
the engine's decks are as good as ppt-master's had only been inferred from the research behind
decision 0010, never measured against ppt-master's real output.

## Shipped
- A page's top-level `<desc id="notes">` becomes the slide's speaker notes, one paragraph per
  line, and is not drawn. The guide asks for notes only when the user wants them (they cost
  output tokens on every page).
- Evaluation: a `notes` check (share of slides with notes); task 12 asks for a script on every
  page; tasks 13 and 14 reuse the sources and briefs of two of ppt-master's published examples
  (`hugohe3/ppt-master-examples`, MIT): the NBS 2025 communiqué briefing (17 pages) and the
  bilingual NEV-exports briefing (15 pages). Their published decks (the native charts/tables
  export) were put in a run folder and checked and judged like ours.

## Checked (2026-10-15, off-peak)
coscribe: `deepseek-flash` at effort low. ppt-master: its published decks (model not stated by
the examples). Judge: `deepseek-flash`, both decks of a task in one request under random labels,
3 rounds; Gemini as a second judge answered 503 on every request.

| Task | Design | Content | Coherence | Facts | Notes | Titles in placeholder |
|---|---|---|---|---|---|---|
| 13 coscribe | 3.90 | 4.30 | 4.33 | 6/6 | 17/17 | yes |
| 13 ppt-master | 3.37 | 3.60 | 4.00 | 6/6 | 17/17 | no |
| 14 coscribe | 4.10 | 4.53 | 4.47 | 8/8 | 16/16 | yes |
| 14 ppt-master | 3.50 | 4.33 | 4.30 | 8/8 | 15/15 | no |
| 12 coscribe | | | | 9/9 | 5/5 | yes |

- coscribe cost 0.25 dollars for the three decks (12: 0.03, 13: 0.12, 14: 0.10), about 1.7 yuan;
  the judge about 0.03 dollars.
- This does not show coscribe's decks are better than ppt-master's. The pages were rendered with
  LibreOffice, which ppt-master's decks are not made for: the judge's worst findings on them are
  rendering faults (a native chart drawn empty, CJK lines in SimSun colliding, data labels
  overlapping), not design faults. Looking at both decks side by side, ppt-master's pages are
  more varied and editorial (large type, illustrations, fewer words a page); coscribe's are
  consistent and dense, many pages repeating one layout of cards, a chart and a table.
- The judge's findings on coscribe's decks are real and the checker missed them: a table running
  into the footer (13, page 4), a footer line overlapping the last bullet (13, page 15), a card's
  English line cut at its edge (14, page 9), body text small for a projector.
- ppt-master's decks put no slide title in the title placeholder: PowerPoint's outline view and
  screen readers see untitled slides; coscribe's have titles.

## Not verified
- Both sets of decks in PowerPoint on Windows, where ppt-master's render as designed.
- A judge from another vendor (Gemini was unavailable).

## Follow-ups
- The checker: a native table's cells and the footer against other text (the misses above).
- Page density and variety: fewer words a page, larger body text, layouts that differ by content.
