# Office route research notes (2026-10-13)

## R1 ppt-master (clone bf89859, 2026-10-13, MIT, 61.5k stars)
- scripts: 197k lines Python (svg_to_pptx 56.7k, pptx_to_svg 20.8k, tests 14.6k, svg_quality 12k, source_to_md 8.1k).
- templates 64 MB (icons 49 MB, sounds 12 MB, brands 1.8 MB, layouts 0.5 MB, charts 0.4 MB); references 3.3 MB (mostly webp examples), workflows 0.4 MB.
- Coupling (static import closure, module-level imports only):
  - drawingml.converter -> 66 modules / 54k lines, pulls attribution_guard, pptx_to_svg, svg_authoring_view...
  - pptx_package.builder -> 80 modules / 71k lines
  - svg_quality.checker -> 34 modules / 27k lines
  - text_measure -> 36 / 22k ; native chart_xml -> 19 / 14k ; table -> 21 / 15k
  - pptx_transitions.py standalone 3.2k ; pptx_animations 5 modules 7.9k (guard via console_encoding)
  - => the core is one web; "vendor a module" is not possible for converter/checker without pulling ~50-70k lines.
    Already vendored before (standalone): formula compiler (_native_formula), animation presets JSON.
- attribution_guard is imported by CLI entry points and console_encoding; MIT license itself only requires the notice.
- Pipeline works as an instrument: init project, spec_lock.md, svg_output/*.svg, checker, svg_to_pptx.
- Output: clean DrawingML; spec colors mapped to theme scheme colors; text as txBox wrap=none spAutoFit;
  SVG <g id> -> group shape name (header/table/chart/note); flat mode: no title placeholders; tables/charts drawn as shapes unless --native-charts-and-tables with JSON payload.
- Converter hard-fails on some invalid input (radial gradient focus outside circle) -> a compile/repair loop is mandatory.
- Checker: 42 check functions; core ones for us: viewbox, fonts, text bounds vs group bounds (font metrics), module overlap, unsupported elements, image refs. Font metrics: font_metrics.json/font_advances.json from Office for Mac fonts (numeric only).
- Design knowledge: executor-base "Page Expression Core" (device menu, layout structures, page recipes, effects defaults) + shared aesthetic baseline: ~25k chars.

## Experiment (ablation), deepseek-flash, off-peak
- T1 Q3 review, A (2k-char technical contract only): 78 s, 6 calls, 50k output tokens; looks consulting-grade (sheet A).
- T1 E (coscribe write_pptx + add_pptx_chart one shot with built-in skill): 81 s, 1 call; plain; product-margin table broken (columns shifted); pie without labels.
- (B/C/D/T2 pending)

## Editability of SVG-route output with coscribe tools (deck T1-A)
- read_pptx: works (grouped text read since 8ci), but every slide title is empty (no title placeholder).
- list_pptx_shapes: CRASH on group shapes: `shape.click_action` raises TypeError for GroupShape (presentations.py _describe_shape ~2974). Product bug -> issue.
- edit_pptx_text edits placeholders only (title/content); edit_pptx_shape / add_pptx_animation / delete use top-level shape_index -> cannot address a text inside a group.
- => editing toolkit is placeholder- and index-centric; needs element addressing (stable names from SVG ids, group paths).

## coscribe presentations.py (7,092 lines, 135 functions; crude split by name)
- generate ~760 (+ _svg_slide 737), templates ~310, animation/transition/audio ~840, QA ~420, read/xml ~380, edit ~1,360, helpers ~2,000.
- => most of the file is editing / motion / QA / XML and stays; the generation part is small.

## R2 routes
- Anthropic pptx skill: new decks via pptxgenjs script; edit via unzip/XML/rezip; QA: markitdown + validate + render + inspect. License: proprietary (source-available) -> ideas only.
- PPTAgent / DeepPresenter (MIT, 5.1k stars, ACL 2026): template mode = edit reference slides; freeform mode = HTML pages -> html2pptx (Node, pptxgenjs, Playwright). PPTEval: Content, Design, Coherence.
- Presenton (Apache-2.0, 11.1k): HTML/Tailwind templates, LLM fills structured fields; export mechanism not stated.
- GenOffice (Apache-2.0, 9.5k): slides = style sheet + outline + one JSON page spec per slide; slides check/audit (overflow, overlap); DOCX block tree spliced back byte-preserving.
- OfficeCLI (Apache-2.0, 31.9k, .NET single binary): path addressing /slide[1]/shape[2], --json, raw XML fallback, render/inspect loop; 350+ formula functions, pivot tables; MCP server.

## R5 leads
- Word: GenOffice block-tree byte-preserving splice; docx-js (MIT) used by Anthropic docx skill; AlpaZZ office-agent-skills (license ?).
- Excel: OfficeCLI formula engine (C#), xlsx-for-ai (formula recalc), Modeleon (Python -> live formulas, Apache-2.0), open-sheet (React -> xlsx).

## T1 B result
- B (A + 25k chars design guidance): 95 s, 6 calls, 67k out; real checker errors 0 first pass; more editorial layouts (split cover/toc, dark closing, side panels). Gain over A visible but moderate.
- Cost per 6-page deck (deepseek-flash off-peak, out ¥4/M, in ¥1/M uncached, ¥0.02/M cached): A ≈ ¥0.20, B ≈ ¥0.27.

## R4 eval design (draft)
- Tasks: ~10 PPT tasks: data review (T1), policy->training (T2), project proposal with timeline/process, product launch (image heavy), academic/report summary from a long doc, user's own template fill, edit an existing deck (change numbers, add a page in style, restyle), CJK+English mixed, dense table page, 15+ page deck (consistency).
- Per deck automatic: compile ok first pass; checker errors; render; text overflow/overlap from PPTX (group-aware); numbers fidelity (every number in deck appears in source); editability probe (scripted: read titles, change a number, recolor accent, add an animation to group X, all through coscribe tools; pass/fail each).
- Model judge: Gemini 3.1 Pro, blind, PPTEval dims (design, content, coherence 1-5) + ranking; PPTEval reports design judge r=0.90 vs humans.
- Maintainer: blind pairwise on Windows PowerPoint for a sample (opens without repair? looks professional?).
- Cost/time per deck from usage.

## T2 (security training, 7 pages)
- A: 114 s, 9 calls (2 pages repaired: userSpaceOnUse gradients, bounds overlap), 82k out. Good look; defects: p2 cards repeat filler "怎么做｜做错会怎样", p6 cards half empty, p7 small text.
- E: 61 s, 1 call; every page the same numbered-icon list; p2 table tiny; centered titles.
- Issue #135 opened: list_pptx_shapes crashes on group shapes.

## Edit via SVG source (deck T1-A)
- e1 number change (华东 5,410 -> 5,600, propagate): 17 s, 6 calls (parallel per page), 20k in / 7.8k out; P01-P03 changed, P04-P06 UNCHANGED; totals 12,900 / +18.0% / 华东 +16.2% all right; bar height 262 -> 271 (= 262*5600/5410). Checker 0 errors.
- e2 recolor whole deck to brand red: 37 s, 6 calls, 20k in / 22k out; all pages consistent; one miss (P5 green highlight card kept). Checker 0 errors.
- T1 C (spec first): 214 s, 8 calls, 58k in / 117k out; most consistent and restrained (footer, page numbers, top accent bar, slope chart for margins = smart chart choice); some empty areas (P2 right, P5); invented "Q3 · 2024" (year not in source) -> fidelity check needed.
- T2 B: 152 s, 9 calls, 109k out; better than T2 A (data-class page with red-line bracket, sanction chain on last page).

## Spike: vendored element emitter + own walker (2026-10-13)
- Copied unmodified: closure of svg_to_pptx.drawingml.elements incl. lazy imports = 37 modules / ~24k lines (+ pptx_shapes/data 612 KB, font metric JSON); no attribution_guard in it.
- Own code: walker.py ~150 lines (tree walk, translate-only transforms, group wrapping with ids as names, solid background promotion, python-pptx packaging).
- Result on T1-A SVGs: renders nearly identical to ppt-master's exporter. Gap: positioned tspan line breaks merged into one line (cover subtitle, p6 card text) -> orchestration-level text-flow handling to port. Not yet: rotate/scale/matrix transforms, gradient backgrounds, native chart/table, images, hyperlinks, slide-level validation.
- => "vendor the element core (MIT, owned copy + NOTICE), write orchestration/packaging/checker ourselves" is feasible.
- T2 C: 251 s, 16 calls (first pass 10 errors on 7 pages, 2 repair rounds), 127k in / 173k out; most consistent motif (corner brackets, big page numbers); defects: p4 watermark "02" (should be 04), p2 empty middle, added facts not in source (".zip/.rar", "版本 v1.0") -> fidelity check.
- Reverse direction: pptx_to_svg.slide_to_svg closure 52 modules / 36.6k lines; union with the emitter 58 modules / 44k lines, no guard. Full roundtrip restore (authoring_roundtrip + workspace) pulls the big web (converter 99 modules / 81k). => lifting a user's own slide to SVG for page redesign is a later, optional phase.

## Cost: the 5.7 yuan (maintainer saw 2,040,016 tokens / ¥5.7)
- Sum of all runs: in 659k (cached 473k), out 1,366k -> out ¥5.47 of ¥5.7 (96%). Not cache.
- Output is mostly reasoning: T1-A 6 SVG pages = 28 KB (~10k tokens) vs 50k output tokens.
- DeepSeek `reasoning_effort` top-level param: none / low / high (default) / max (docs api-docs.deepseek.com create-chat-completion). Verified: none -> no reasoning tokens; low 579 vs high 1430 on the same prompt.

## Effort runs (same outline)
| run | s | calls | out | ¥ | first-pass errors |
| T1 A / A2 (high) | 78/97 | 6/7 | 50k/58k | 0.20/0.24 | ?/1 |
| T1 AL (low) | 54 | 6 | 34k | 0.14 | 0 |
| T1 AN (none) | 28 | 8 | 15k | 0.07 | 5 |
| T1 B / B2 (high) | 95/120 | 6/7 | 67k/89k | 0.27/0.36 | 0/1 |
| T1 BL | 154 | 7 | 71k | 0.32 | 4 |
| T1 BN | 37 | 11 | 23k | 0.12 | 10 |
| T2 A / A2 | 114/121 | 9/9 | 82k/86k | 0.33/0.35 | 11/15 |
| T2 AL | 85 | 9 | 48k | 0.20 | 4 |
| T2 AN | 29 | 9 | 16k | 0.07 | 7 |
| T2 B / B2 | 152/176 | 9/7 | 109k/138k | 0.45/0.55 | 3/0 |
| T2 BL | 113 | 12 | 85k | 0.35 | 10 |
| T2 BN | 34 | 11 | 26k | 0.12 | 12 |
- Eye check: BN T1 cover title + hero number invisible (white on white), invented "2026 财年", bar labels clipped; AN T2 p3 text below the canvas, p5 title over header band. AL T1 ≈ A quality.
- => none is cheap but breaks geometry/contrast the checker does not catch (contrast + canvas overflow checks needed); low ≈ high for A at -35% cost; B low not cheaper.

## Judge (Gemini 3.5 Flash, blind, T1 seed 7): A2 4.9/4.8/4.9, B2 4.8, B 4.7, C 4.6, A 4.3, D 3.2, E 2.1 (design). Run-to-run variance (A 4.3 vs A2 4.9) ≈ condition differences. Pro models: no quota on this key; 3.7/3.8 flash 503.
