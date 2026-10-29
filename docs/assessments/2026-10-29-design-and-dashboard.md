# Design note: Design pages and Dashboards (2026-10-29)

Design before code: it adds a kind of artifact (Dashboard) and widens another (Design). Status:
**proposed**. It rests on 0001 (a fixed, cached tool list), 0015 (artifacts that run their own
JavaScript are drawn in a sandboxed frame), 0020 (design systems are a library), 0021 (scripts) and
0027 (an artifact is what coscribe made from a source it owns; a table to look at is a Dashboard).

## 中文摘要

1. **Design 放宽范围**：现在的 Design 只会做图标/Logo 选项表（技能 `svg-design`）。改成"一页视觉作品"：
   海报、单页宣传、社交图、界面草图/落地页、信息图、图标。仍然是一个自包含的 .html，沙箱里显示。
   技能改写；Design 也能像 Slides 一样选一个设计系统；面板加浅色/深色切换。
2. **Dashboard 新增**：看数据的页面（指标卡、图表、表格、筛选）。**页面和数据分开放**：
   `销售看板.html`（布局和代码，头部带 `coscribe: dashboard` 标记）+ `销售看板.dashboard/data/*.json`（数据）。
   服务端显示时把数据注入页面，沙箱仍然不联网。好处：刷新只改数据不改代码；人能看到页面用的是哪份数据；
   导出时拼成一个自包含 HTML。
3. **图表库**：沙箱不联网，所以由服务端提供一个内置图表库，页面声明要用就注入。建议 ECharts 6.1.0
   （Apache-2.0，约 1.1 MB，看板需要的图表类型、缩放、提示都有）；备选 Chart.js 4.6.1（MIT，约 210 KB，轻但能力少）。
4. **刷新**：第一版"刷新"= 让 coscribe 在对话里重新取数写 data；之后看板可带一个 `refresh.py`，
   保存成固定工作流/定时任务按时刷新（和工作流、定时任务现有机制对接，不新造）。
5. **让 AI 看见自己做的页面**：现在模型写完 HTML 看不到效果。加一个只读的"看一眼"能力（页面截图返回给模型），
   Design 和 Dashboard 共用。
6. **需要你拍板**：图表库选哪个；第一版刷新是否只做"对话里刷新"；Design 的范围是否按第 1 条放宽。

## 1. What exists

- A Design is an `.html` file a conversation wrote (`conversation/artifacts.py` maps `.html` to
  `design`), served by `web/routes/design.py` with `sandbox allow-scripts; default-src 'none'`:
  its own script and style run, nothing reaches the network. A card draws the page scaled; the
  panel (`DesignPanel`) redraws on every write; Export gives HTML and PDF (print dialog).
- The skill `svg-design` teaches one thing: icon and logo option sheets (sizes on light and dark).
  The first-message note for a Design start says the same (`runtime_lg/messages.py`).
- Dashboard is a tile marked "Soon"; `useArtifactStart` sends no note for it.
- The model never sees a page it wrote: no tool renders HTML back to it.

## 2. Design, widened

**Scope.** A Design is one visual made as one page: icon and logo sheets (as now), a poster or
flyer, a one-page summary meant to be looked at rather than edited, a social image, a UI mock-up or
landing page, an infographic. Not a deck (Slides), not writing to edit (Doc), not a data view
(Dashboard).

**Skill.** `svg-design` becomes `Design`, with a short part per kind: fixed canvas sizes for
posters and social images (the page is the canvas, at its real pixel size), real text not text in
pictures, inline SVG for drawings, system fonts with a CJK fallback stack, no network. The icon
sheet rules stay as one of the parts.

**Design system.** A Design start may name a library design system, as a Slides start does (the
chip's menu, a note in the first message): the page uses its colours, fonts and radii as CSS
variables.

**Theme.** The panel gets a light/dark switch: the frame's `color-scheme` is set from it, so a page
written with `prefers-color-scheme` follows the switch rather than the operating system.

## 3. Dashboard

**Source.** A page and its data, apart:

- `sales.html`: layout and code, with `<meta name="coscribe" content="dashboard">` in its head (an
  `.html` without it stays a Design);
- `sales.dashboard/data/<name>.json`: the data, one file per dataset (rows as objects, or
  `{columns, rows}`), written by coscribe from the person's files, a connector or a script;
- later, `sales.dashboard/refresh.py`: how to make the data again.

**Serving.** The route reads the page and its data files and adds, before the page's own scripts,
`<script>window.coscribe={data:{...}, updated:"..."}</script>` and the chart library if the page
asks for it (`<script data-coscribe-lib="charts"></script>`). The policy is the Design one: no
network, so nothing the page does reaches outside, and the data reaches the page only through the
server.

Why apart: a refresh rewrites data, never code, so a scheduled refresh cannot break the page; the
person (and coscribe at its next turn) can see which data the page shows and when it was made; a
data file is small to diff and to check; Export joins them into one self-contained HTML.

**Charts.** The frame has no network, so the server carries one chart library, vendored with its
licence. Recommended: ECharts 6.1.0 (Apache-2.0, 1.12 MB minified): line, bar, pie, scatter,
heatmap, gauge, treemap, maps by registration, zoom and rich tooltips, the types a dashboard needs;
models write its options well. Alternative: Chart.js 4.6.1 (MIT, 210 KB): lighter, fewer types, no
zoom without plugins. A card's thumbnail loads the library too; with many dashboards on the
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

1. Dashboard source and serving: the marker, registry kind `dashboard`, the route with data and the
   vendored library injected, the tile enabled with its first-message note, the panel (the Design
   frame), Export HTML with data inlined. Tests: registry, route headers and injection.
2. The Dashboard skill, then a live run on 6 briefs (DeepSeek, off-peak), judged from screenshots.
3. Design widened: the skill rewritten, the design-system choice for a Design start, the theme switch.
4. `look_at_page`, used by both skills; the same 6 briefs plus 6 Design briefs again.
5. Dashboard data in the panel (made when, CSV export) and Refresh v1; then v2 with `refresh.py` and
   a saved workflow.

## 6. Questions for the maintainer

1. Chart library: ECharts (recommended) or Chart.js?
2. Refresh in v1 only through the conversation, with the saved-workflow refresh after?
3. Design widened as in section 2?

## Not verified

- Library sizes and licences were read from the npm registry and jsDelivr on 2026-10-29.
- Whether DeepSeek writes good ECharts options inside this sandbox: step 2 measures it.
- The offscreen-window screenshot in the desktop shell (step 4) is not built or tried yet.
