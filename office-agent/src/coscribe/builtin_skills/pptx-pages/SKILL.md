---
name: PPTX Pages
description: How to build a new PowerPoint deck as one SVG page per slide with build_pptx_from_pages -- the workflow, the page language, layout and colour choices, and how to edit a deck built this way. Load before writing any new deck.
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
3. **Fix the look once** for the whole deck: a palette (one dominant colour, one support, one
   accent, plus two or three neutrals for text and backgrounds, all as #RRGGBB), a type scale, the
   margins, and one recurring motif (a band, a rule, a corner shape). Every page reuses them.
4. **Write the pages** with write_file into a folder next to the deck, e.g. `q3-review-pages/`,
   named so they sort in order: `01-cover.svg`, `02-agenda.svg`, ... Write every page before the
   first build, and write each one carefully once: every extra round trip costs the user money.
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

Not for this way: a deck on the user's own template or a deck the user brought (use the template
and edit tools), or a request to change a few words in an existing deck.

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

- Sizes: title 36-44, subtitle or takeaway line 20-26, body 18-22 (never under 16 on a content
  page), captions and sources 13-14, hero numbers 56-120. Bold for the title and for one or two
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
