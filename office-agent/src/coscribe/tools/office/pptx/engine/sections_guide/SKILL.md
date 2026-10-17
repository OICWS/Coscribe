---
name: Slides
description: How to build a new PowerPoint deck as one HTML section per slide with build_pptx_from_pages -- the workflow, the section language, layout and colour choices, and how to edit a deck built this way. Load before writing any new deck.
---
A deck built this way is a folder of slide sections, one `.html` file per slide, compiled into a
.pptx whose text, shapes, tables and charts stay editable in PowerPoint. The sections are the
deck's source: to change the deck later, edit the sections and build again. Design guidance below
is condensed in part from ppt-master's design references (MIT licence, copyright Hugo He).

## Workflow

1. **Read the material** the user gave (read_docx / read_xlsx / read_pdf / read_file). Every
   number, name and date on a slide comes from it; a figure you compute (a sum, a share) must be
   exact. Never add a year, a version number or a statistic the material does not have: no date
   on the cover or in a footer unless the material gives one. Write a figure with its unit as the
   material writes it ("399 元" stays "399 元", not "¥399"; "41%" stays "41%"), because the reader
   checks the slide against the material.
2. **Plan the deck** before writing: one line per slide with its role (cover, agenda, section,
   content, closing), its title (a short claim, not a label: "华东增长最快", not "区域数据"), and
   the figures it must show. A breakdown keeps all its parts (every share of a survey, every
   price of an offer); before writing slides, check that each figure in the material is on a
   slide or left out on purpose. One idea per slide. Slide count as the user asked; otherwise
   about one slide per two minutes of talk.
3. **Write the design spec** (section "Design spec" below) into `design.md` in the deck folder,
   after reading the one visual-style file it picks. Every slide follows it.
4. **Write the slides** with write_file into a folder next to the deck, e.g. `q3-review.slides/`,
   named so they sort in order: `01-cover.html`, `02-agenda.html`, ... Write every slide before
   the first build, and write each one carefully once: every extra round trip costs the user
   money. Speaker notes for a talk deck, or when the user asks for them (讲稿, 演讲者备注): what
   the presenter says on that slide, in its `<aside>`, a few sentences, not the slide's text
   again.
5. **Build once**: build_pptx_from_pages(pages_dir="q3-review.slides", path, sources=[the
   material's files]). It builds a folder of `.html` sections as it builds SVG pages; the page
   language in its own description is for SVG pages, this skill's is for sections. Fix every
   error it reports by editing the named slide, then build again; at most two repair rounds. Fix
   the warnings that are real (an invented number, faint body text) in the same edits; do not
   rebuild for a warning you decide to keep (an axis tick, a watermark).
6. **Look once**: when the build has no errors, render_pptx_preview(path) once and change only
   what is clearly wrong, with one more build at most.

To redesign a deck the user made ("美化", a rough draft to make presentable): read_pptx gives
every slide's text, tables, chart data and pictures; keep all of it, the pictures saved into the
deck folder, pass the old deck in `sources` so the number check holds the new slides to it, and
write the new deck under a new name.

To edit a deck built this way: edit the slide's `.html` (edit_file) and build again; for a change
that touches every slide (a colour, a font), edit each slide. If the build refuses because the
.pptx was changed after it was built (in PowerPoint, or with the edit_pptx_* tools), do not pass
replace_changes on your own: either make the change with the edit_pptx_* tools on the .pptx, or
ask the user whether their changes may be replaced.

Not for this way: a deck on the user's own template (load "PPTX Pages": it builds on templates),
changing a deck the user brought (use the edit tools), or a few words in an existing deck.

## The section language

A slide is one `<section>` of well-formed XHTML on a 1920 x 1080 canvas. Close every tag, write
`<br/>` and `<img .../>`, write characters, not entities (`&nbsp;` is an error; escape & < > as
&amp; &lt; &gt;). Anything outside this language is an error that names what to write instead.

```html
<section style="background:#F7F5F0; font-family:Microsoft YaHei, Arial; color:#1F2937"
         data-transition="fade">
  <x-shape id="band" data-shape="rect"
           style="left:0px;top:0px;width:1920px;height:12px;background:#C2410C"/>
  <h1 id="title" style="left:120px;top:96px;width:1680px;height:96px">华东增长最快</h1>
  <p id="lead" style="left:120px;top:220px;width:860px;height:120px;font-size:36px;color:#4B5563">
    收入同比增长 <b>23.5%</b>，达到 <span style="color:#C2410C;font-weight:700">5,410 万元</span>。</p>
  <ul id="points" style="left:120px;top:400px;width:860px;height:400px;font-size:36px">
    <li>华东区新签客户 <b>42</b> 家</li>
    <li>续约率升至 91%</li>
  </ul>
  <aside>先讲收入，再讲续约。</aside>
</section>
```

- **Every element is placed by its box**: `left`, `top`, `width` and `height` in px, in its
  `style`. Nothing flows from one element to the next; elements are drawn in document order, the
  later on top. Keep text inside a 96 px margin.
- **Text**: `h1`, `h2`, `h3`, `p`, `ul` and `ol` (with `li`). The text wraps inside the box's
  width, as in PowerPoint; the box must be tall enough for its lines, or the build says how tall
  it needs to be. Inside text: `b`, `i`, `u`, `br` and `span` (`color`, `font-weight`,
  `font-style`, `font-size`). A text's style takes `font-size` (px), `font-weight`, `font-style`,
  `font-family`, `color`, `text-align` (left, center, right, justify), `line-height` (a number,
  1.0-2.5), `vertical-align` (top, middle, bottom), `padding` (px) and `background` (a filled
  box). Defaults: h1 64 px bold, h2 48, h3 36, others 28 px; line height 1.15 for h1-h2, 1.35
  for body.
- **The slide's title** is the text with `id="title"`: it becomes the slide title (outline view,
  accessibility, edit_pptx_text).
- **Shapes**: `<x-shape data-shape="rect|round-rect|ellipse|triangle|arrow|line">` with
  `background`, `border` ("2px solid #RRGGBB" or "dashed"), `border-radius` (round-rect) and
  `opacity`. A shape holds no text: put a `p` over it. A `line` is drawn by its border, from the
  box's top-left to its bottom-right corner.
- **Pictures**: `<img src="photo.jpg" style="...; object-fit:cover"/>`, the file in the deck
  folder; `cover` crops to fill the box, `contain` fits it whole.
- **Drawings**: `<svg viewBox="0 0 W H" style="left;top;width;height">` holds an illustration in
  SVG (rect, circle, ellipse, line, polyline, polygon, path, text, g, gradients, a drop-shadow
  filter), drawn into its box whole. Presentation attributes only (`fill="#..."`), no `style` or
  `class` inside it.
- **Tables** and **charts** (below) and **icons**: `<x-icon data-icon="ship" style="...;
  color:#0E3A66"/>`, the names in read_skill_file("PPTX Pages", "icons.md").
- **Background**: the section's `background`. Its `font-family` and `color` are every text's
  default.
- **Speaker notes**: `<aside>`, one paragraph per line.
- **Motion** (only when asked for or the deck is presented): `data-transition` on the section
  (`fade`, `push`, or `magic`, which moves elements with the same id from the previous slide to
  this one, as PowerPoint's Morph), `data-build-in` on an element (`fade`, `rise`, `pop`; one
  click each, in document order).
- Colours are #RRGGBB. No `em`, `%`, `var()`, `margin`, classes, scripts or links; at most 200
  elements a slide.

## Design spec

A deck looks designed when one decision runs through every slide. Before any slide, choose:

1. **Talk or read**: whether someone presents the deck or people read it on their own. The user
   decides, not the style: take it from the request ("汇报", "演讲", "听众", a talk → talk; "发给",
   "阅读", "读者", a report to send round → read). When the request does not say and you can ask,
   ask once with ask_user_question, the two choices in one line each; a deck made with no one to
   ask is read.
   - **Talk**: the speaker carries the content, the slide carries one point. A claim title, then
     one figure, chart or picture, or at most three short lines; body 36-42 px. What the speaker
     will say is in the speaker notes, not on the slide. In two languages, the second one is a
     smaller line under the title and the key points only.
   - **Read**: the slide stands on its own, as a document would. Full statements, tables and
     sources are fine; body 27-33 px, annotations 21-24. Still one idea per slide, and room
     between blocks.
2. **A visual style**: how the deck looks. Pick one from the list by the content and audience, read
   its file with read_skill_file("PPTX Pages", "visual-styles/<id>.md"), and no other style file.
   Its sizes are for a 1280-wide page: multiply them by 1.5.
3. **A method** (optional): how the deck argues, for a kind of deck the list names; read
   read_skill_file("PPTX Pages", "methods/<id>.md"). Its fallback colours and typography are
   defaults the spec may take.

Then write `design.md` in the deck folder, short, with exactly these parts:

- **Use**: talk or read, and how the request said it.
- **Direction**: the style's id and one sentence that names this deck's look (e.g. "双语公报：数据
  新闻式栅格，中文主行与英文副行成对").
- **Palette**: field, surface, ink, primary, accent (and at most two more), each as #RRGGBB with
  its job. The accent marks the key figure only.
- **Type**: the families by role, from fonts every Windows PC has: Chinese titles SimSun (serif,
  authority) or Microsoft YaHei / SimHei (sans); Chinese body Microsoft YaHei or DengXian; Latin
  and figures Cambria, Georgia or Times New Roman (serif) or Arial, Calibri, Segoe UI (sans);
  Consolas for code. At most three families. A text sets its own `font-family`
  ("SimSun, Cambria") when it differs from the section's. Sizes in px: display 84-120, title
  54-66, lead 36-42, body as talk or read sets it, annotation 24-27 (21-24 when read), source
  line 20-21.
- **Grid**: margins (84-120 px), columns, the gap between blocks, the corner radius (0 for a
  hard-edged style).
- **Recurring elements**: what sits in the same place on every content slide (a header rule, a
  section index, a source line) and what the cover and the section slides share.
- **Slides**: one line each, its role and its composition (a hero number, chart and takeaway, a
  table, a comparison, a timeline, cards...). No three slides in a row with the same
  composition; a dense slide is followed by a lighter one.

Visual styles (`visual-styles/<id>.md`): `swiss-minimal`, `editorial`, `data-journalism`,
`brutalist`, `photo-editorial`, `soft-rounded`, `glassmorphism`, `dark-tech`, `blueprint`,
`ink-wash`, `ink-notes`, `sketch-notes`, `chalkboard`, `paper-cut`, `memphis`, `zine`,
`vintage-poster`, `pixel-art`; the "PPTX Pages" skill describes each in one line.

Methods (`methods/<id>.md`): `operating-review` (business reviews: result, variance, cause, owned
action), `consulting-decision` and `mbb-consulting` (answer-first decision documents),
`solution-proposal`, `investor-pitch`, `product-launch`, `creative-pitch`, `narrative-keynote`,
`academic-research`, `science-explainer`, `technical-deepdive`, `incident-postmortem`,
`workshop-teaching` (training), `duty-manual` (rules and procedures). Their mentions of
confirmation steps, workspaces and image rows belong to the project they come from: take the
method and the defaults, not the procedure.

## Layout

Canvas 1920 x 1080. Keep text inside a 96 px margin. A title zone of about 150 px at the top,
the content field below it, an optional footer line at the bottom.

Pick the structure from how the content relates, not from habit:

| Content | Structure |
|---|---|
| One claim or one number | A single focus: the number large (108-180 px) with one line of context, lots of space |
| Two things compared | Two matched halves with one difference marked, or a table |
| A few parallel points (3-4) | Columns or a row of cards with the same treatment |
| Steps or a timeline | A line with nodes, or chevrons, labels above or below |
| Evidence and its conclusion | An uneven split: the chart or table large (60-70%), the takeaway beside it |
| A whole and its parts | A centre with satellites, or a stacked bar |

Vary the structure from slide to slide; a deck of identical card grids reads as a template.
After a dense slide, a lighter one. A card is an `x-shape` (round-rect) with its texts placed
over it, each inside the card's box with the card's padding.

## Type and colour

- Sizes: as the design spec fixes them (body never under 36 on a talk slide, 27 on a read
  slide). Bold for the title and for one or two load-bearing words or numbers per sentence, not
  for whole paragraphs.
- Left-align body text. A line should not end with a single character: give the box the width
  its phrase needs.
- Colour by proportion: the dominant colour on about 60% of the visual weight, the support on
  30%, the accent on 10% (the key number, the one word that matters). Green for up and red for
  down only when the content has a direction.
- Contrast: body text at least 4.5:1 against what is behind it; secondary grey text not lighter
  than about #6B7280 on white. White text needs a dark field under all of it.
- Depth comes from spacing and tints, not shadows. Cards in a row stay flat.

## Charts and tables

A chart or a table is a native PowerPoint chart or table, not drawn shapes: the user can change
its data in PowerPoint.

```html
<x-chart id="revenue-chart" style="left:96px;top:240px;width:840px;height:720px">
{"type": "column", "categories": ["华东", "华南", "华北"],
 "series": [{"name": "Q3 营收（万元）", "values": [5410, 3980, 2120],
             "point_colors": ["#C2410C", "#94A3B8", "#94A3B8"]}],
 "data_labels": {"number_format": "#,##0"}, "font_size": 27,
 "style": {"colors": ["#94A3B8"], "text_color": "#374151", "grid_color": "#E5E7EB"}}
</x-chart>
```

- The JSON holds the data and its look; the box is the element's style, never in the JSON.
- `type`: column, bar (horizontal; categories top-down), line, area, pie, doughnut. Several
  series for a comparison, with `"show_legend": true`; `point_colors` on a column or bar series
  marks the bar the point is about.
- Values are the material's numbers as plain numbers (5410, not "5,410"); `number_format`
  writes them: "#,##0", "0.0", and `0"%"` for a share written as 41 (shows 41%). `font_size`
  is in px like the slide.
- Negative values: `"axes": {"category": {"label_position": "low"}}`, so the category names
  sit below the plot instead of on the bars.
- The text above the chart says the finding with its figure ("位置便利占 41%，居首"), not the
  axis: the reader, and the checks, read the figure there.

```html
<table id="regions" style="left:1020px;top:270px;width:804px;height:390px;font-size:27px;
       border-color:#E5E7EB">
  <tr><th style="background:#0F172A;color:#FFFFFF">区域</th><th>营收（万元）</th><th>同比</th></tr>
  <tr><td>华东</td><td style="text-align:right">5,410</td>
      <td style="text-align:right;color:#15803D;font-weight:bold">+12.2%</td></tr>
  <tr><td>华北</td><td style="text-align:right">2,120</td><td style="text-align:right">-3.1%</td></tr>
</table>
```

- Leading rows of `<th>` are the header; the first header cell's `background` and `color` are the
  header's. A cell takes `text-align`, `color`, `background` and `font-weight`, `colspan` and
  `rowspan`; column widths come from `<colgroup><col style="width:Npx"/>...</colgroup>`. Every row
  is written as the material writes it; numbers right-aligned.
- A long table goes over two slides rather than below 24 px.

## Icons

An icon is one element: `<x-icon data-icon="ship" style="left:150px;top:300px;width:72px;
height:72px;color:#0E3A66"/>` (an `id` names it for the edit tools). The names are listed in
read_skill_file("PPTX Pages", "icons.md"): trending-up, users, building-factory, ship, target,
shield-check, calendar, coin, bolt, leaf, rocket and about 280 more; a wrong name is reported with
the nearest ones. Use them where they carry meaning (a category, a step, a status), one size per
role, never drawn from scratch.

## Illustrations

A picture the deck needs (a cover scene, a section divider, a metaphor beside a point) is drawn in
an `<svg>` element, and the build turns every part of it into a shape the user can recolour and
move. Draw it flat, from the deck's palette: a few large shapes (`path` with curves, `polygon`,
`circle`, `ellipse`, `rect`), layered back to front, about 40 shapes at most. A silhouette reads
better than detail: a ship is a hull, a deck and two funnels. No `<mask>` or `<pattern>`.

One illustration on the cover and section slides at most, none on a slide of numbers. Text keeps
a plain area of its own: never on top of the drawing's busy part.

## Photos

A photograph earns its place when the content is a real place, product, team or event; otherwise
draw (above) or let the slide's figures carry it. The user's own pictures come first: those in
the material, in the workspace, or inside a deck they gave you (read_pptx lists them; save each
into the deck folder with run_python_script: a python-pptx picture's `image.blob`, `image.ext`).
Without them, and only when the deck's style is built on photographs, search_licensed_images (an
English query, orientation "landscape") returns openly licensed images; download_image the chosen
one into the deck folder. Never search_images for a deck: its results carry no licence. Place a
photo with `<img src="store.jpg" style="...; object-fit:cover"/>`, text over it only on a dark
`x-shape` scrim, and for an "attribution-required" result its `attribution_text` as a 20-21 px
credit line on the same slide. One search per photo, at most three photos a deck unless the user
asks for more.

## Avoid

- A text box too short for its lines (the build reports it); long sentences on slides (split
  them).
- Decoration with no job: stripes down every edge, gradients on body text, icons drawn from
  scratch instead of taken from the icon set.
- Every slide the same layout; every card with a shadow.
- Light grey text on a light background; text over a picture without a dark scrim under it.
- Facts, dates or numbers the material does not have.
