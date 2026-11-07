# The Design evals again, with parts, in-place text and the properties panel in (shipped)

Why: since the last run (`design-run3`, 2026-10-31), the Design skill has gained:

- parts several artboards share;
- the note that the person edits pages in the properties panel;
- the check that every placed part exists.

The run checks that DeepSeek still makes working canvases, and whether it writes parts unprompted.

## Shipped
- `evals/design_route.py` counts the parts the pages place (`parts`, with how many pages place
  each). A part that is placed but never written (`missing_parts`) fails the brief. Tested in
  `tests/test_evals_design_route.py`.

## Measured
`python -m evals.design_route` with `deepseek:deepseek-flash`, effort `low`, all 7 briefs, run on
2026-11-03 at about 21:20 Beijing time (off-peak):

| task | tile | made | looked | boards | variables used | links | parts | errors | overflow | ok | cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 01-landing | yes | yes | 1 | 2 | 10/10 | 0 | 0 | 0 | 0 | yes | 0.039 |
| 02-logo-options | yes | yes | 1 | 3 | 10/10 | 0 | 0 | 0 | 0 | yes | 0.050 |
| 03-poster | yes | yes | 1 | 1 | 8/8 | 0 | 0 | 0 | 0 | yes | 0.022 |
| 04-social | no | yes | 1 | 3 | 4/4 | 0 | 0 | 0 | 0 | yes | 0.019 |
| 05-onboarding | no | yes | 1 | 3 | 9/9 | 5 | status x3 | 0 | 0 | yes | 0.017 |
| 06-launch-zh | yes | yes | 1 | 2 | 7/7 | 0 | 0 | 0 | 0 | yes | 0.027 |
| 07-prototype | yes | yes | 1 | 4 | 10/10 | 14 | statusbar x4 | 0 | 0 | yes | 0.034 |

- **Overall:** 7 of 7 made and working, 0.21 USD in all (0.26 in the last run).
- **Parts:** both multi-screen phone designs wrote their status bar as a part and placed it on
  every screen, unprompted. Neither wrote its bottom bar as a part: the prototype's menu has a
  "View cart" bar only on that screen, so nothing else was repeated there.
- **Links:** the prototype links its four screens in both directions (14 links, none broken).
- **Variables:** every variable declared is used.
- **Looks:** `look_at_page` ran once per brief, against 2 to 16 last time. Every brief still
  passed, but the model fixes less after looking.

## Not verified
- Designs are scored by checks and a look at the screenshots, not by the vision judge.
- One run per brief: the counts move from run to run.
