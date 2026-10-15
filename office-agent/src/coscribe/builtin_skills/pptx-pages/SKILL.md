---
name: PPTX Pages
description: How to build a new PowerPoint deck as one SVG page per slide with build_pptx_from_pages -- the workflow, the page language, layout and colour choices, a deck on the user's own template, and how to edit a deck built this way. Load before writing any new deck.
---
A deck built this way is a folder of SVG pages, one per slide, compiled into a .pptx whose shapes
and text stay editable in PowerPoint. The pages are the deck's source: to change the deck later,
edit the pages and build again. Design guidance below is condensed in part from ppt-master's design
references (MIT licence, copyright Hugo He).

## Workflow

1. **Read the material** the user gave (read_docx / read_xlsx / read_pdf / read_file). Every
   number, name and date on a slide comes from it; a figure you compute (a sum, a share) must be
   exact. Never add a year, a version number or a statistic the material does not have: no date
   on the cover or in a footer unless the material gives one. Write a figure with its unit as the
   material writes it ("399 元" stays "399 元", not "¥399"; "41%" stays "41%"), because the reader
   checks the slide against the material.
2. **Plan the deck** before drawing: one line per page with its role (cover, agenda, section,
   content, closing), its title (a short claim, not a label: "华东增长最快", not "区域数据"), and
   the figures it must show. A breakdown keeps all its parts (every share of a survey, every
   price of an offer); before writing pages, check that each figure in the material is on a
   page or left out on purpose. One idea per page. Page count as the user asked; otherwise about
   one page per two minutes of talk.
3. **Write the design spec** (section "Design spec" below) into `design.md` in the pages folder,
   after reading the one visual-style file it picks. Every page follows it.
4. **Write the pages** with write_file into a folder next to the deck, e.g. `q3-review-pages/`,
   named so they sort in order: `01-cover.svg`, `02-agenda.svg`, ... Write every page before the
   first build, and write each one carefully once: every extra round trip costs the user money.
   Speaker notes only when the user asks for them (a talk, 讲稿, 演讲者备注): what the presenter
   says on that page, in its `<desc id="notes">`, a few sentences, not the slide's text again.
5. **Build once**: build_pptx_from_pages(pages_dir, path, sources=[the material's files]). Fix
   every error it reports by editing the named page, then build again; at most two repair rounds.
   Fix the warnings that are real (an invented number, faint body text) in the same edits; do not
   rebuild for a warning you decide to keep (an axis tick, a watermark).
6. **Look once**: when the build has no errors, render_pptx_preview(path) once and change only
   what is clearly wrong, with one more build at most.

To edit a deck built this way: edit the page's SVG (edit_file) and build again; for a change that
touches every page (a colour, a font), edit each page. If the build refuses because the .pptx was
changed after it was built (in PowerPoint, or with the edit_pptx_* tools), do not pass
replace_changes on your own: either make the change with the edit_pptx_* tools on the .pptx (a word
or a number: edit_pptx_text with find, on every slide at once; a shape: list_pptx_shapes, then its
name or path), or ask the user whether their changes may be replaced.

Not for this way: changing a deck the user brought (use the edit tools), or a few words in an
existing deck.

## Design spec

A deck looks designed when one decision runs through every page. Before any page, choose:

1. **A visual style**: how the deck looks. Pick one from the list by the content and audience, read
   its file with read_skill_file("PPTX Pages", "visual-styles/<id>.md"), and no other style file.
2. **A method** (optional): how the deck argues, for a kind of deck the list names; read
   read_skill_file("PPTX Pages", "methods/<id>.md"). Its fallback colours and typography are
   defaults the spec may take.

Then write `design.md` in the pages folder, short, with exactly these parts:

- **Direction**: the style's id and one sentence that names this deck's look (e.g. "双语公报：数据
  新闻式栅格，中文主行与英文副行成对").
- **Palette**: field, surface, ink, primary, accent (and at most two more), each as #RRGGBB with
  its job. The accent marks the key figure only.
- **Type**: the families by role, from fonts every Windows PC has: Chinese titles SimSun (serif,
  authority) or Microsoft YaHei / SimHei (sans); Chinese body Microsoft YaHei or DengXian; Latin
  and figures Cambria, Georgia or Times New Roman (serif) or Arial, Calibri, Segoe UI (sans);
  Consolas for code. At most three families. A text sets its own `font-family`
  ("SimSun, Cambria") when it differs from the root's. Sizes in px: display 56-80, title 36-44,
  lead 24-28, body 20-24 (never under 20 on a content page), annotation 16-18, source line 13-14.
- **Grid**: margins (56-80 px), columns, the gap between blocks, the corner radius (0 for a
  hard-edged style).
- **Recurring elements**: what sits in the same place on every content page (a header rule, a
  section index, a source line) and what the cover and the section pages share.
- **Pages**: one line each, its role and its composition (a hero number, chart and takeaway, a
  table, a comparison, a timeline, cards...). No three pages in a row with the same composition;
  a dense page is followed by a lighter one.

Visual styles (`visual-styles/<id>.md`):

| id | Look |
|---|---|
| `swiss-minimal` | Strict grid, sharp geometry, aggressive whitespace, near-zero decoration |
| `editorial` | Magazine hierarchy: columns, hairline rules, serif and sans interplay |
| `data-journalism` | Economist / Bloomberg infographic: dense grid, hero numbers, sidebars, source lines |
| `brutalist` | Newspaper density, heavy rules, raw structure |
| `photo-editorial` | Photography leads, text as captions and points |
| `soft-rounded` | Rounded cards, gentle elevation, approachable (product, training) |
| `glassmorphism` | Frosted-glass panels, gradient light (SaaS, product) |
| `dark-tech` | Dark canvas, luminous accents, geometric precision (tech, AI, launches) |
| `blueprint` | Engineering schematic: line work on dark paper, annotated |
| `ink-wash` | New-Chinese ink wash: rice paper, brush, seal red |
| `ink-notes` | Whiteboard ink, minimal hand-drawn marks |
| `sketch-notes` | Warm hand-drawn sketchnotes |
| `chalkboard` | Classroom chalkboard |
| `paper-cut` | Layered cut paper, soft shadows |
| `memphis` | Pop colour blocks, geometric confetti |
| `zine` | Risograph zine, halftone, limited palette |
| `vintage-poster` | Mid-century print poster |
| `pixel-art` | 8-bit retro game |

Methods (`methods/<id>.md`): `operating-review` (business reviews: result, variance, cause, owned
action), `consulting-decision` and `mbb-consulting` (answer-first decision documents),
`solution-proposal`, `investor-pitch`, `product-launch`, `creative-pitch`, `narrative-keynote`,
`academic-research`, `science-explainer`, `technical-deepdive`, `incident-postmortem`,
`workshop-teaching` (training), `duty-manual` (rules and procedures). Their mentions of
confirmation steps, workspaces and image rows belong to the project they come from: take the
method and the defaults, not the procedure.

The style files and methods are ppt-master's (MIT licence, copyright Hugo He; `NOTICE.md`).

## On the user's own template

When the user names their template (a .pptx or .potx), the deck is built on it:

1. build_pptx_from_pages(pages_dir, path, template="公司模板.pptx") with the pages folder still
   empty returns the template's `viewBox`, theme `colours` and `fonts`, its `layouts`, and each
   `example_slides` entry's layout, `background` and `decoration` (bands, panels, pictures with
   their box and fill).
2. Fix the look from it, not from a visual style's defaults: the template's colours (the decoration's fills
   first; they are what the template looks like), its fonts, and its decoration's place.
3. Each page's root takes `data-template-slide="N"`: the slide starts with example slide N's
   background and decoration, and the page draws only the content, around them and in colours
   that read on that background. A cover starts from the template's cover, a content page from
   a content slide, a closing page from its last slide. No page draws a full background.
4. Build with the same `template`; every later build passes it too.

## Layout

Canvas 1280 x 720. Keep text inside a 64 px margin. A title zone of about 100 px at the top, the
content field below it, an optional footer line at the bottom.

Pick the structure from how the content relates, not from habit:

| Content | Structure |
|---|---|
| One claim or one number | A single focus: the number large (72-120 px) with one line of context, lots of space |
| Two things compared | Two matched halves with one difference marked, or a table |
| A few parallel points (3-4) | Columns or a row of cards with the same treatment |
| Steps or a timeline | A line with nodes, or chevrons, labels above or below |
| Evidence and its conclusion | An uneven split: the chart or table large (60-70%), the takeaway beside it |
| A whole and its parts | A centre with satellites, or a stacked bar |

Vary the structure from page to page; a deck of identical card grids reads as a template. After a
dense page, a lighter one.

## Type and colour

- Sizes: as the design spec fixes them (body never under 20 on a content page). Bold for the title and for one or two
  load-bearing words or numbers per sentence, not for whole paragraphs.
- Left-align body text. Break lines at phrase or punctuation boundaries; a line should not end
  with a single character.
- Colour by proportion: the dominant colour on about 60% of the visual weight, the support on 30%,
  the accent on 10% (the key number, the one word that matters). Green for up and red for down only
  when the content has a direction.
- Contrast: body text at least 4.5:1 against what is behind it; secondary grey text not lighter
  than about #6B7280 on white. White text needs a dark field under all of it.
- Depth comes from spacing and tints, not shadows: at most two or three shadowed objects per page
  (feDropShadow, dy 4-8, opacity 0.06-0.10). Cards in a row stay flat.

## Charts and tables

A chart or a table is a native PowerPoint chart or table, not drawn shapes: the user can change
its data in PowerPoint, and its JSON is shorter than drawing it. The group holds the JSON only:

```xml
<g id="revenue-chart" data-pptx-replace-with="chart"><metadata type="application/json">
{"x": 64, "y": 160, "width": 560, "height": 480, "type": "column",
 "categories": ["华东", "华南", "华北"],
 "series": [{"name": "Q3 营收（万元）", "values": [5410, 3980, 2120],
             "point_colors": ["#C2410C", "#94A3B8", "#94A3B8"]}],
 "data_labels": {"number_format": "#,##0"}, "font_size": 18,
 "style": {"colors": ["#94A3B8"], "text_color": "#374151", "grid_color": "#E5E7EB"}}
</metadata></g>
```

- `type`: column, bar (horizontal; categories top-down), line, area, pie, doughnut. Several
  series for a comparison, with `"show_legend": true`; `point_colors` on a column or bar series
  marks the bar the point is about.
- Values are the material's numbers as plain numbers (5410, not "5,410"); `number_format`
  writes them: "#,##0", "0.0", and `0"%"` for a share written as 41 (shows 41%). `font_size`
  is in px like the page.
- Negative values: `"axes": {"category": {"label_position": "low"}}`, so the category names
  sit below the plot instead of on the bars.
- The text above the chart says the finding with its figure ("位置便利占 41%，居首"), not the
  axis: the reader, and the checks, read the figure there.

```xml
<g id="regions" data-pptx-replace-with="table"><metadata type="application/json">
{"x": 680, "y": 180, "width": 536, "height": 260, "schema": "ppt-master.semantic-table.v2",
 "columns": ["区域", "营收（万元）", "同比"],
 "rows": [["华东", {"text": "5,410", "align": "r"},
           {"text": "+12.2%", "align": "r", "color": "#15803D", "bold": true}],
          ["华北", {"text": "2,120", "align": "r"}, {"text": "-3.1%", "align": "r"}]],
 "style": {"font_size": 18, "header_fill": "#0F172A", "header_text": "#FFFFFF",
           "band_fill": "#F1F5F9", "border_color": "#E5E7EB"}}
</metadata></g>
```

- A cell is a string, or `{"text", "align": "r"}` for a number, plus `bold`, `color`, `fill` to
  mark the cell the point is about. Every row is in `rows`, written as the material writes it.
- A long table goes over two pages rather than below 16 px.

## Avoid

- A text box that runs past its card or the page; long sentences on slides (split them).
- Decoration with no job: stripes down every edge, gradients on body text, icons drawn from
  scratch that look like clip art.
- Every page the same layout; every card with a shadow.
- Light grey text on a light background; text over a picture without a dark scrim under it.
- Facts, dates or numbers the material does not have.
