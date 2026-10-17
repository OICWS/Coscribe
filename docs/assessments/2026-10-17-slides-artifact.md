# Slides artifact: design checklist v1

Design draft, 2026-10-17, for the maintainer to go through item by item before any editor code.
It follows the Claude Slides screens the maintainer walked through on 2026-10-17, group by group.
For each item: what Claude does (as seen in those screens), what coscribe would do, and what is
still to decide. Once the open items are settled this becomes decision record 0015 (artifacts) and
the build order in section 14.

## 中文摘要

- **是什么**：coscribe 生成的演示文稿成为一个 Slides artifact：工作区里的一个文件夹，每页一个
  受限的 HTML 片段。在应用里看、评论、做基本编辑，导出 PPTX / PDF / PNG / HTML。用户点名要
  .pptx 时，同时自动导出一份 .pptx 放在旁边。
- **最大的一个决定（第 1 节）**：页面源格式。建议改用“绝对定位的 HTML”：每个元素有自己的
  框（x, y, 宽, 高），和 PowerPoint 的对象模型一一对应；文字在框内自动换行，中文输入法、列表、
  表格都由浏览器原生处理。插图和图表仍用现有的 SVG → 原生形状编译器。代价：要写一个
  HTML → PPTX 编译器，并且必须先在现有评测上不输给 SVG 路线（0010 的规则）才能换。
- **只有改过的部分才可能有损（第 11 节）**：导入的 pptx 保留原文件；没改的页导出时原样复制
  原来的 XML，只有改过的页由源重新生成。
- **AI 与人的编辑**：人改过的页，AI 覆盖写入会被拒绝（人优先）；每轮对话开始时，AI 收到一条
  消息，列出用户改过的页。撤销 Ctrl+Z 也能撤销 AI 的一轮修改。
- **在 PowerPoint 里改**：沿用 build.json 的逐页哈希，检测出在 PowerPoint 里改过的页，只把
  这些页重新导入（有损），并告诉 AI。
- **顺序**：格式和编译器（无界面，先评测）→ 只读面板（看、缩略图、放映、导出）→ 评论和发给 AI
  → 编辑 → 导入 pptx → PowerPoint 往返。

### 需要你定的（每项我给了建议）

| # | 问题 | 建议 |
|---|---|---|
| D1 | 页面源格式：SVG（现有）还是绝对定位 HTML | 绝对定位 HTML，SVG 只用于插图（第 1 节） |
| D2 | 画布尺寸：1920×1080 还是现有 1280×720 | 1920×1080（第 1.4 节） |
| D3 | 页面放在沙箱 iframe 里，还是校验后直接画在我们的界面里 | Slides 校验后直接画（无脚本可言）；iframe 沙箱留给 Design/Dashboard（第 2 节） |
| D4 | 导入的页没改时显示什么：原页的渲染图，还是转换后的 HTML | 先显示转换后的 HTML，差得多的页标出来（第 11 节） |
| D5 | “只重生成改过的”按页还是按形状 | 第一版按页，之后按形状（第 11 节） |
| D6 | 评论导出到 PPTX 吗 | 不导出；评论只在应用里（第 5 节） |
| D7 | 形状菜单有哪些 | 矩形、圆角矩形、椭圆、三角、箭头、直线、连接线（第 4 节，待你对照截图） |
| D8 | 新建页插在当前页之后还是末尾 | 当前页之后（第 7 节，待你确认 Claude 的行为） |
| D9 | Canvas 视图里点一页是跳到那页还是只选中 | 单击选中，双击跳到该页（第 8 节） |
| D10 | 属性面板在右侧还是底部 | 右侧，与批注栏同一位置（第 6 节） |

## 1. The page source format (decide first)

Everything below depends on it: how the editor edits, how the model writes, how export works.

### 1.1 Option A: keep the SVG pages (decision 0010)

- What exists: `build_pptx_from_pages` compiles a folder of SVG pages (viewBox 1280×720) to
  native PowerPoint shapes, checks them and writes `build.json` with a hash per page and per slide.
  Measured in 0010: about 2 points (of 5) better than the old tool-per-shape route at a similar price.
- Against it for an editor:
  - **Text never wraps** in the page language: every line is its own `<tspan>`. Typing into a
    paragraph means re-breaking lines ourselves, on every keystroke, with font metrics we do not
    have in the browser for every font.
  - **No editing support in the browser**: SVG `<text>` has no usable caret, selection, IME
    composition or lists. All of that would be written by us.
  - Tables are a `<metadata>` JSON blob, not something one can click into.

### 1.2 Option B: positioned HTML sections (recommended)

- One `<section>` per slide, 1920×1080, a closed set of elements and inline styles, close to the
  Claude Slides format: `h1`–`h3`, `p`, `ul`/`ol`, `img`, `table`, `svg`, and a few custom
  elements (`x-shape`, `x-icon`, `x-chart`, `x-connector`).
- **Difference from Claude's format: every top-level element is positioned** (`left`, `top`,
  `width`, `height` in px; no flow layout between elements). This is PowerPoint's own object
  model: one element = one shape, a group = a group shape. It means:
  - the compiler needs no browser to lay out the page: each element's box is in its style;
  - the only thing two renderers can disagree on is where lines break inside a box, which the
    checker measures (overflow) as it does now;
  - drag, resize and align in the editor change four numbers;
  - a .pptx imports into the same model shape by shape.
- **Text flows inside its box**: `contenteditable` gives caret, selection, Chinese IME, lists and
  tables for free, and PowerPoint wraps the same text box the same way (`wrap="square"`).
- **Drawings stay SVG**: an `<svg>` element inside a section is compiled by the existing
  SVG → DrawingML code (`tools/_native_svg`) into native shapes. A chart is `x-chart` with its data
  and becomes a native, editable chart, like `data-pptx-replace-with="chart"` today.
- Against it:
  - a new compiler, HTML subset → PPTX (text boxes, tables, pictures, lists, the style subset);
  - **0010's rule applies**: the route ships only if it is at least level with the SVG route on
    the deck evaluation (blind judge plus checks). The measured gain came from the model writing
    each page whole in one pass, which this keeps; the risk is the model's layout skill in HTML vs
    SVG, which only the evaluation shows.

### 1.3 Option C: both

SVG pages for generation, converted to HTML for editing. Rejected: two sources for one slide, and
every edit would have to convert back.

### 1.4 Canvas size (D2)

- 1920×1080, as Claude: 1 px = 1/144 in on a 13.333 × 7.5 in slide, text sizes read naturally
  (body at least 24 px). The SVG pages' 1280×720 scale by 1.5 when an old deck is opened.
- 4:3 and other sizes: `deck.json` holds the canvas; the first version offers 16:9 only.

## 2. Storage and safety

- **A folder in the workspace**: `<name>.slides/` holding `deck.json` (title, order, sections,
  canvas, theme), `slides/<id>.html`, `assets/` (images), `comments.json`, and for an import
  `source.pptx` (the original, never modified). Slide ids are stable; order lives in `deck.json`,
  so reordering touches one file.
- **Exported files sit next to the folder** (`<name>.pptx`, `<name>.pdf`). When the user named an
  Office format, the .pptx is exported on every AI turn that changed the deck, so the file they
  asked for always exists.
- **The future file panel** shows `<name>.slides/` as one item that opens the Slides panel.
- **Rendering (D3)**: a Slides page has no scripts, event handlers or external URLs by
  construction: the validator rejects any element or attribute outside the subset, before a write
  is accepted. So the pages are drawn in our own DOM (in a shadow root, so their styles cannot
  leak), which the editor needs anyway to place a caret and selection handles. The agreed sandboxed
  iframe is for Design/Dashboard artifacts, which run their own JavaScript; drawing Slides there
  would cut the editor off from the page (a sandboxed iframe without `allow-same-origin` is only
  reachable by messages).
- **Images** are files in `assets/`, served by the thread file route; a remote image is downloaded
  when written, never hot-linked.

## 3. Selecting and the format bar

- Claude: click an element to select it; a floating bar above it holds the text style preset
  (Lead/Body), colour, B, I, U, link, list, align, add comment and more.
- coscribe, the same bar, with:
  - **click** selects the element; **double-click** (or typing) enters its text;
  - **drag** moves, eight handles resize, Shift keeps proportions; arrow keys nudge 1 px
    (Shift: 10 px); Delete removes;
  - **style presets** come from the deck's theme (Title, Heading, Lead, Body, Caption), so a
    preset change stays consistent across slides;
  - **colour** offers the theme colours first, then custom (the same picker as the properties
    panel);
  - **"More"** holds: bring forward/back, duplicate, align to slide, lock.
- Multi-select (Shift+click, drag a box) and group: in the first editing version, moving and
  deleting several; grouping later.
- Not in the bar, on purpose: anything else is asked for in a comment or the conversation (the
  maintainer's rule: few features, the rest by asking the AI).

## 4. Inserting

- Claude: text box (T), image (file picker), table (3×3 with a header row), shapes dropdown.
- coscribe, the same four. A new element lands in the centre of the slide, selected, with the
  theme's Body style.
- Image: from the file picker or pasted; copied into `assets/`.
- Table: 3×3 with a header row; Tab moves between cells, Tab in the last cell adds a row. Merged
  cells: by asking the AI.
- **Shapes (D7)**: the screenshots did not show the dropdown open. Proposed: rectangle, rounded
  rectangle, ellipse, triangle, arrow, line, connector. Each maps to a PowerPoint preset geometry.

## 5. Comments and sending to the AI

- Claude: comment mode, click any element; the popover names its place ("Slide 1 › Body '…'"),
  @Claude, and a "Send to Claude" checkbox.
- coscribe:
  - anchors by slide id and element id (every element gets an id when written), shown as
    "Slide 3 › Body 'Revenue grew…'";
  - "Send to coscribe" puts the comment in the composer as a quote with its anchor; sending it
    starts a turn, and the AI's reply is posted as an answer in the thread;
  - a comment whose element is deleted keeps its slide anchor and says so;
  - stored in `comments.json`, so they survive restarts and travel with the folder.
- **Export (D6)**: comments stay in the app. PowerPoint's comments are a separate part of the file;
  writing them is possible later if asked for.

## 6. Properties panel

- Claude: slide transition and background colour, with a Theme/Custom colour picker.
- coscribe: the same two for a slide; with an element selected, also its position and size
  (numbers), and its build-in animation.
- Where (D10): on the right, where the comment rail sits, one or the other open at a time.

## 7. Managing slides

- Claude: "+" opens New slide with ten layouts (Blank, Title, Section, Title + body, Bullets, Two
  columns, Table, Quote, Image + caption, Closing), previewed on the current slide's background.
- coscribe: the same ten layouts, generated from the deck's theme (a layout is a section with
  placeholder text), so they match a deck the AI made.
- Inserted after the current slide (D8: to confirm in Claude).
- Thumbnails: drag to reorder; right-click: duplicate, delete, hide, add a section before.
- Speaker notes: the book icon opens an editable notes area under the slide; stored in the
  section's `<aside>` (at most 4,000 characters, as Claude); exported to the slide's notes.

## 8. Views

- Claude: Slide view and Canvas view (a grid of all slides with their section descriptions); a
  chevron hides the thumbnails, leaving a floating mini bar (previous, page, next, notes, show
  thumbnails).
- coscribe: the same. In Canvas view a click selects, a double-click opens the slide (D9), and a
  comment can be put on a whole slide.
- Thumbnails are the same DOM scaled down, drawn only while visible, so a 100-slide deck stays fast.

## 9. Zoom and undo

- Claude: zoom in/out (Ctrl + / Ctrl −), fit, 25–200 %; undo Ctrl+Z, redo Ctrl+Shift+Z.
- coscribe: the same. Editing works at any zoom (the page is scaled with a CSS transform;
  Chromium keeps the caret and the IME window in place under a transform, to be checked on Windows
  with Microsoft Pinyin).
- **Undo includes the AI**: one AI turn that changed the deck is one undo step ("Undo coscribe's
  change to slides 2–4"). Undoing it writes the previous sources back and tells the AI in the next
  turn's message.
- History is kept for the session; the folder's previous versions are kept by the workspace's own
  history if there is one, not by us.

## 10. Present and export

- **Present** (Claude: Present, and Present with notes; full screen with previous, page, next,
  notes, full screen F, exit):
  - full screen in its own window; with notes, a presenter view on the second screen when there is
    one;
  - transitions `fade`, `push`, `magic` (a matching element moves between slides); build-ins
    `fade`, `rise`, `pop`.
- **Export** (Claude: PDF, HTML, PNG of this slide, PPTX with current fonts, PPTX with basic fonts):
  - **PPTX** from the compiler: every element is a native, editable object; transitions map to
    Fade, Push and Morph; build-ins to the Fade, Rise Up and Zoom entrance effects. Unchanged
    imported slides are copied from the original file (section 11).
  - **"Current fonts" vs "basic fonts"**: the first keeps the deck's fonts (the viewer needs them
    installed, or embedded where the licence allows), the second maps them to fonts every Office
    machine has (Microsoft YaHei / Arial / Times New Roman). Exactly what Claude's two options do
    is not known; this is our reading of the labels.
  - **PDF** printed from the rendered slides (vector, no LibreOffice, decision 0012); **PNG** of the
    current slide at 1920×1080; **HTML** as one file with a small player.
  - Every export runs the checks first (overflow, off-slide, contrast) and says what it found.

## 11. Opening a .pptx: only what was edited can lose anything

- On open, `source.pptx` is kept untouched and each slide is converted into a section: text boxes,
  pictures, tables, preset shapes and groups map directly; anything the subset cannot express
  (SmartArt, a video, a custom geometry, an effect) becomes a picture of itself plus a marker
  "shown as an image; edit it in PowerPoint or ask coscribe".
- Each section records the hash of the slide it came from. On export:
  - a slide whose section is unchanged is **copied from `source.pptx` as it was** (its XML, media,
    notes and animations);
  - a slide that was edited is compiled from its section, and only it can differ from the original.
- **By slide first (D5)**: an edit to one word regenerates the whole slide. Later, by shape: keep
  the slide's XML and replace only the edited shapes, so a typo fix leaves the rest of the slide
  verbatim.
- **What the user sees for an untouched slide (D4)**: the converted section, so it is editable at
  once. Where conversion lost something visible, the thumbnail carries a mark and the slide can be
  shown as the original's picture (PowerPoint's own render on Windows, our SVG preview otherwise).
- Word and Excel follow the same rule later, by paragraph and by sheet.

## 12. The AI and the user working on the same deck

- **The model writes sections with the file tools** (`write_file` / `edit_file` on
  `slides/<id>.html`, `deck.json` for order), like the SVG pages today, and calls one check/export
  tool (replacing or extending `build_pptx_from_pages`; the tool list stays fixed, decision 0001,
  so this is one reviewed change).
- **The user's edits reach the AI as a message**, never in a schema or the system prompt: at the
  start of each turn, "the user changed slides 3 and 5 since your last read; comments: …".
- **Human edit wins**: a write to a slide the user changed after the model last read it is refused
  with "read it again first", as Claude refuses a publish over a hand edit.
- **Edited in PowerPoint**: `build.json`'s per-slide hashes already detect a deck changed after
  export. The same check, run when the panel opens or the AI is about to export, finds the changed
  slides, re-imports only those (section 11) and tells the AI. The Office add-ins remain the way to
  work with the AI inside PowerPoint itself.

## 13. Panel and window

- The deck opens in the viewer panel (decision 0014) and, like every panel, in a window of its own
  (#387). Present opens its own full-screen window.
- Claude's panel menu (Move, Fill and arrange, Open in new window) is the menu every panel has now.

## 14. Order of work (one PR each, each usable on its own)

1. **Format, validator and compiler, no UI**: the subset written down, HTML → PPTX for the
   elements in section 1.2, the checks; the deck evaluation run against the SVG route. Stop here
   if it loses.
2. **Read-only Slides panel**: render, thumbnails, Slide/Canvas views, zoom, present, export.
3. **Comments and "Send to coscribe"**.
4. **Editing**: select, move, resize, text with the format bar, insert, notes, new slide, reorder,
   undo including AI turns.
5. **Opening a .pptx** with verbatim slides.
6. **PowerPoint round trip**: detecting slides changed outside and re-importing them.

## 15. Not known yet (inferred from the screenshots, to confirm)

- The shapes dropdown's contents (D7).
- Whether Claude inserts a new slide after the current one or at the end (D8).
- Whether a click in Canvas view opens the slide (D9).
- What Claude's "current fonts" and "basic fonts" PPTX exports differ in.
- Whether Claude's slide elements are positioned or flow; its format allows `table` and `svg`
  and bans `margin`, which suggests boxes, but the screenshots do not show it.
- Caret and IME behaviour under zoom on Windows (to test once step 4 exists).
