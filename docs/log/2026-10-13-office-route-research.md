# Research: the route for Word, Excel and PowerPoint (shipped: report and proposed decision)

Why: the maintainer asked whether coscribe's way of making office files is right, given that
`hugohe3/ppt-master` makes much better decks at the same price, and set the direction: be a good
host, reuse open-source code where the licence allows, write the rest; PowerPoint, then Excel,
then Word.

## Shipped
- `docs/assessments/2026-10-13-office-route.md`: measurements on two briefs and 17 generated decks
  (coscribe's route vs whole-page SVG with or without design guidance, a design spec, a checker
  repair round, three reasoning-effort levels), blind judging, two source-edit tests, the coupling
  of ppt-master's code and a spike that reuses its 24k-line element emitter with ~150 lines of our
  own; other routes (Anthropic's skill, PPTAgent, Presenton, GenOffice, OfficeCLI); the proposed
  architecture, plan and sizes. Contact sheets in `docs/assessments/2026-10-13-office-route/`.
- `docs/decisions/0010-office-files-are-compiled-from-whole-page-sources.md`, status proposed.
- Issue #135: `list_pptx_shapes` crashes on group shapes (found while testing editability).

## Not verified
- Nothing ran on Windows or in real PowerPoint: rendering was LibreOffice on Linux, with
  WenQuanYi standing in for Microsoft YaHei.
- The judge was Gemini 3.5 Flash for one round per brief (the key's free quota ran out) and
  deepseek-flash for the rest, which also generated the decks; a Pro-class judge was not available.
- Only deepseek-flash generated decks; other providers are untested.

## Follow-ups
- The maintainer decides on 0010; then phase P0 (the evaluation in the repository) and P1 (the
  engine MVP), as listed in the report's section 7.
