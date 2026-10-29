# Design note: Design pages and Dashboards (2026-10-29)

Design before code: it adds a kind of artifact (Dashboard) and turns another (Design) into a canvas. Status:
**proposed**. It rests on 0001 (a fixed, cached tool list), 0015 (artifacts that run their own
JavaScript are drawn in a sandboxed frame), 0020 (design systems are a library), 0021 (scripts) and
0027 (an artifact is what coscribe made from a source it owns; a table to look at is a Dashboard).

## 中文摘要

1. **Design 改成画布 + 画板**（参照 Claude 的 Design，维护者给的截图）：一个画布上摆几个画板，可平移缩放，
   并排比较方案；每个画板是一个普通的自包含 HTML，各自在沙箱里显示。默认浏览/选中，切到 Play 才能交互。
   不照搬它的 `.dc.html` 模板语法；可调参数用 CSS 变量，对接已有的设计系统。第一版靠对话改，面板只改
   文字和变量；属性面板、画笔、便签放后面。用途：界面稿、原型、海报、单页、流程图；数据是假的。
2. **Dashboard 新增**：长期看真实数据的页面。**页面和数据源分开**：`销售看板.html`（普通 HTML + JS，头部带
   标记）+ `销售看板.dashboard/datasets.json`（登记每个数据源：来自哪个文件、连接器查询或脚本，何时更新）
   和数据文件。页面不写死数字：占位符标 `data-source`，由脚本填；派生数字（通过率）单独声明算法；
   点任何数字都能看到来源和更新时间（参照 Claude 的 Dashboard："每个数字都标明来源"）。
   服务端显示时注入数据，沙箱不联网。
3. **图表库**：沙箱不联网，所以由服务端提供一个内置图表库。候选 ECharts 6.1.0（Apache-2.0，约 1.1 MB，
   开箱好看、代码少）和 d3 v7（Claude 的 Dashboard 用它：底层、灵活、代码多）。第 2 步两个都实测再定。
4. **刷新**：第一版"刷新"= 让 coscribe 在对话里重新取数写 data；之后看板可带一个 `refresh.py`，
   保存成固定工作流/定时任务按时刷新（和工作流、定时任务现有机制对接，不新造）。
5. **让 AI 看见自己做的页面**：现在模型写完 HTML 看不到效果。加一个只读的"看一眼"能力（页面截图返回给模型），
   Design 和 Dashboard 共用。
6. **需要你拍板**：Design 是否按画布 + 画板做；第一版刷新是否只做"对话里刷新"。

## 1. What exists

- A Design is an `.html` file a conversation wrote (`conversation/artifacts.py` maps `.html` to
  `design`), served by `web/routes/design.py` with `sandbox allow-scripts; default-src 'none'`:
  its own script and style run, nothing reaches the network. A card draws the page scaled; the
  panel (`DesignPanel`) redraws on every write; Export gives HTML and PDF (print dialog).
- The skill `svg-design` teaches one thing: icon and logo option sheets (sizes on light and dark).
  The first-message note for a Design start says the same (`runtime_lg/messages.py`).
- Dashboard is a tile marked "Soon"; `useArtifactStart` sends no note for it.
- The model never sees a page it wrote: no tool renders HTML back to it.

## 2. Design: a canvas of artboards

The reference is Claude's Design artifact, as the maintainer showed it (a screenshot, and Claude's
own account of it, which was not checked against its source): a canvas index (`canvas.json`: the
artboards, their position and size, notes, pages) and one HTML file per artboard, drawn in sandboxed
frames on a canvas that pans and zooms, with a Play mode for the artboards' own interaction, a
properties panel that edits inline styles and a "Tweaks" panel for declared parameters.

**Use.** Mock-ups and prototypes, several options side by side, a poster or a one-page summary to
look at, a flow chart, a phone screen. The data in it is made up. Not a deck (Slides), not writing to
edit (Doc), not a page of real data (Dashboard).

**Source.** `name.design/canvas.json` and one `.html` per artboard beside it. An artboard is a plain,
self-contained page (inline SVG, system fonts with a CJK fallback, its own script). Claude's
`.dc.html` template syntax (`{{ }}`, `sc-for`, a logic class) is not copied: plain HTML and script are
what a model writes most reliably. Its tweakable parameters are CSS variables declared in its head,
which is also how a library design system (0020) is applied: choosing a system sets the variables.
Today's single `.html` Design reads as a canvas of one artboard.

**Canvas.** Pan and zoom, select and move an artboard, Play to use its interaction, a light/dark
switch (the frames' `color-scheme`). Editing in v1 is through the conversation, plus text and the
declared variables in a panel; a properties panel for inline styles, drawing tools and notes come
later.

**Skill.** `svg-design` becomes `Design`: when a Design is the right output, the canvas and artboard
files, artboard sizes (desktop, phone, poster, social), several options as several artboards, the
variables, no network. The icon-sheet rules stay as one part.

## 3. Dashboard

**Source.** A page and its data, apart:

- `sales.html`: layout and code, with `<meta name="coscribe" content="dashboard">` in its head (an
  `.html` without it stays a Design);
- `sales.dashboard/datasets.json`: one entry per dataset, with where it comes from (a workspace
  file, a connector query, a script), when it was last made and its columns; and derived figures
  (a pass rate as passed / total) declared with their formula;
- `sales.dashboard/data/<dataset>.json`: the rows, written by coscribe or by a refresh;
- later, `sales.dashboard/refresh.py`: how to make the data again.

**Every number shows where it came from** (the rule of Claude's Dashboard type, read from its
description): the page writes no figure itself. An element holds a placeholder and
`data-source="<dataset>"` (or a derived figure's name), the page's script fills it from
`window.coscribe`, and the panel shows, for any figure, chart or table, its dataset, formula and when
it was made. A checker flags a page whose text holds figures with no source. Claude keeps a
dashboard in the artifact's own database, read with each viewer's own rights; coscribe is local and
for one person, so the same parts are files beside the page, and a connector query runs at refresh
time, not when the page opens.

**Serving.** The route reads the page and its data files and adds, before the page's own scripts,
`<script>window.coscribe={data:{...}, updated:"..."}</script>` and the chart library if the page
asks for it (`<script data-coscribe-lib="charts"></script>`). The policy is the Design one: no
network, so nothing the page does reaches outside, and the data reaches the page only through the
server.

Why apart: a refresh rewrites data, never code, so a scheduled refresh cannot break the page; the
person (and coscribe at its next turn) can see which data the page shows and when it was made; a
data file is small to diff and to check; Export joins them into one self-contained HTML.

**Charts.** The frame has no network, so the server carries one chart library, vendored with its
licence. Candidates: ECharts 6.1.0 (Apache-2.0, 1.12 MB minified: the chart types a dashboard needs,
zoom and tooltips, good defaults, little code) and d3 7.9.0 (ISC, 280 KB; Claude's Dashboard type ships d3 v7: low
level, any chart, more code for the model to get right). Step 2 runs the same briefs with each and
picks one; Chart.js 4.6.1 (MIT, 210 KB) is the light fallback. A card's thumbnail loads the library too; with many dashboards on the
Artifacts page that argues for a server-drawn thumbnail later, whichever library is chosen.

**Panel.** The Design panel's frame, plus: when the data was made, Refresh, and Export (HTML with
data inlined, PDF, each dataset as CSV).

**Refresh.** V1: Refresh opens the dashboard's conversation (or a new one rooted at it) with "refresh
the data", and coscribe rewrites the data files. V2: a dashboard carries `refresh.py`; saving it as a
fixed workflow (a script step that writes `data/`) makes the refresh repeatable without a model and
schedulable as a task, under 0021 like any script. This uses workflows and scheduled tasks as they
are; it adds no runner of its own.

**Skill.** `Dashboard`: when a Dashboard is the right output (a table or figures the person wants to
look at, filter or keep current; not a one-off chart in a Doc), the source layout, the injected
`window.coscribe`, the chart library, a layout of KPI cards over charts over a detail table, number
formats, empty and loading states, light and dark.

## 4. Letting coscribe see its page

A deferred, read-only tool `look_at_page(path)` returns a screenshot of a Design or a Dashboard as
the app draws it (desktop shell: an offscreen window loading the same route; the web build: the
browser panel's own screenshot of it). The skills ask for one look before saying a page is done. The
tool list stays fixed (0001): it is one more deferred tool, and the path arrives as an argument.

## 5. Steps (one PR each, about 600 lines at most)

1. Dashboard source and serving: the marker, `datasets.json`, registry kind `dashboard`, the route
   with data and the vendored library injected, the tile with its first-message note, the panel,
   Export HTML with data inlined. Tests: registry, route headers and injection.
2. The Dashboard skill and the source checker, then a live run on 6 briefs with each chart library
   (DeepSeek, off-peak), judged from screenshots.
3. Where a number came from, in the panel; Refresh v1; then v2 with `refresh.py` and a saved workflow.
4. Design canvas: `canvas.json`, artboards in frames, pan, zoom, select, move, Play, theme switch.
5. The Design skill rewritten, design-system variables, editing text and variables in a panel.
6. `look_at_page`, used by both skills; the briefs again.

## 6. Questions for the maintainer

1. Design as a canvas of artboards (section 2)?
2. Refresh in v1 only through the conversation, with the saved-workflow refresh after?
3. The chart library is picked in step 2 from a measured run (ECharts or d3), unless you prefer one now.

## Not verified

- Library sizes and licences were read from the npm registry and jsDelivr on 2026-10-29.
- Whether DeepSeek writes good ECharts options inside this sandbox: step 2 measures it.
- The offscreen-window screenshot in the desktop shell (step 6) is not built or tried yet.
- How Claude's Design and Dashboard work comes from the maintainer's screenshot and Claude's own
  answers, not from their source.
