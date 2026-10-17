# File viewers: Word review, slides and sheets as panels

Design, 2026-10-17. Recorded as decision
[0014](../decisions/0014-office-files-are-shown-in-the-app-as-panels.md). The look was set by the
mockups the maintainer reviewed on 2026-10-16 (Word review beside the chat, slides with a
filmstrip, a sheet grid with a formula bar); the panel layout they sit in shipped in #334, #337
and #338.

## 中文摘要

- **形式**：查看器是一个面板，和任务详情、浏览器、后台任务一样，可拖动、可铺满。从对话里的文件卡片、任务详情的“输出”、工具行打开；一个面板里切换本次对话的多个文件。
- **Word**：
  - 页面由 docx-preview（Apache-2.0）在前端画出，修订照样显示。
  - 右侧批注栏、连线和回复框由我们自己画，数据来自后端读出的批注和修订列表。
  - 接受/拒绝修订、回复、解决批注、对选中文字加批注，都由后端改真实文件，然后重新渲染。模型也能用同样的操作（新工具）。
- **PPT**：沿用现有的页面预览（SVG 或 Office 渲染）和点选形状；没有预览时退回到文字大纲。
- **Excel**：由应用自己画表格，数据是文件里存的值和公式（值由 IronCalc 算出），带格式、列宽、合并单元格和工作表标签，图表先显示占位。这推翻了 2026-10-16 “Excel 1d 不做”的结论，理由见第 5 节。
- **顺序**：Word 后端 → Word 面板 → PPT 面板 → Excel 面板，每步一个 PR。

## 1. What the viewers are for

- **See the result without leaving the app.** The model writes a Word, PowerPoint or Excel
  file; the user wants to look at it beside the conversation, not in another program.
- **Review it.** In Word, read the tracked changes and comments, accept or reject a change,
  answer or resolve a comment. These are real Word changes and comments, so the file opens in
  Word the same way.
- **Point at part of it.** Select words, a shape or cells and ask coscribe about them; the
  selection reaches the composer as a quote with its place in the file.
- **See what this run changed.** The file card says so, and the viewer marks it where it can.

Not in scope: editing text freely in the viewer (that is Word's job; "Open in Word" is always
there), and showing Office itself inside the app (dropped on 2026-10-15, see the Excel design,
section 5).

## 2. Where they live

- **One viewer panel** (`PanelId` `viewer`) in the panel layout, beside Task details, Browser and
  Background tasks: it can be dragged, filled and closed like them.
- **Opened from** a file card in the conversation, a row under Task details' Outputs, or the file
  name in a tool row. It shows one file at a time, with a switcher for the files this conversation
  has opened in it.
- **Header**: file name, "Changed in this run" when it is, the view switch (Word only), "Open in
  Word/PowerPoint/Excel" (the existing `open_in_os`), then the panel's expand and close.
- **Refresh**: when a tool writes the open file, the panel reloads it.
- **Fetching**: the file's bytes come from the existing thread file route
  (`GET /api/threads/{id}/files/download?path=`); nothing is copied.

## 3. Word

### Rendering

- **docx-preview** 0.4.1 (Apache-2.0; its one dependency, JSZip, is MIT/GPLv3 dual, used under
  MIT): about 75 KB plus 98 KB minified, loaded only when the viewer opens a Word file.
- **Checked on the redline from the live run** (`service_agreement_redline.docx`, two tracked
  changes and two comments):
  - It draws the page, the title and heading styles, and the changes. Each insertion and
    deletion is its own `<ins>`/`<del>` element, in document order.
  - Each comment gets one `docx-comment-ref` marker.
- **The three views**:
  - **Review**: `renderChanges: true`.
  - **Final**: `renderChanges: false`. It draws the text with every change accepted (checked:
    "2,650 GBP", "45 days").
  - **Original**: the backend returns a copy with every change rejected; docx-preview has no such
    mode.
- **Its own comment popovers are hidden.** The comment rail is ours (section 3.2), placed by the
  `docx-comment-ref` markers.
- **Limits**, stated in the panel where they matter:
  - pages break only where the file has a page break (no automatic pagination);
  - fonts missing on the machine are substituted;
  - fields such as a contents list are not computed.
- **docx-preview calls its change and comment rendering experimental**, so the viewer checks its
  output against the backend's list. When the count of `<ins>`/`<del>` elements or comment
  markers differs from the list, the rail is shown without connectors and the change controls
  sit in the rail instead of on the page.

### 3.2 The review model and the comment rail

- **Read route**: `GET /api/threads/{id}/docx-review?path=` returns, in document order:
  - **changes**: id, kind (`insert` / `delete`), author, date, text, and the heading it falls
    under;
  - **comments**: id, author, date, text, the words it is anchored to, `done`, and its replies.
- **Where it comes from**: replies and `done` come from `commentsExtended.xml` (`w15:paraIdParent`,
  `w15:done`, Word 2013 and later); the ids from `commentsIds.xml`; authors from `people.xml` when
  present.
- **The rail** follows the mockup:
  - cards aligned to their anchors and pushed down when they overlap, with a connector line;
  - the active card raised, with a reply box, Reply and Resolve;
  - a resolved comment folds to one line;
  - above the page: "N changes · M comments" with previous and next, and Accept all / Reject all.

### 3.3 Changes go through the backend

Every action rewrites the real file with one operation and the panel re-renders it:

| Action | Operation |
|---|---|
| Accept or reject a change | `accept_change` / `reject_change` (id) |
| Accept or reject all | `accept_all` / `reject_all` |
| Reply to a comment | `reply` (comment id, text): a new comment whose `w15:paraIdParent` is the parent's paragraph |
| Resolve or reopen | `resolve` / `reopen` (comment id): `w15:done` |
| Comment on a selection | `comment` (anchor text, text) |

- **One function serves both callers**: the route `POST /api/threads/{id}/docx-review` and a model
  tool.
- **The tools** are a read and an edit, `read_docx_review` and `edit_docx_review` (operations
  list, like `edit_docx_structure`). They are new deferred tools, so the tool schema snapshot
  changes in a reviewed PR (decision 0001).
- **Author**: actions taken in the panel carry the computer's user name, as Word does until a
  name is set (a name in Settings is a follow-up); the model's carry "Coscribe".
- **The model learns** of the user's panel actions from the file the next time it reads it. A
  conversation message for each action is not sent.

### 3.4 Selecting and asking

A selection on the page shows a small bar: Ask coscribe, Comment, Copy.
- **Ask coscribe** puts a quote into the composer: the file, the heading the selection falls
  under, and the selected text.
- **Comment** opens a card in the rail for a new comment on those words; saving it runs the
  `comment` operation.

## 4. PowerPoint

- **Pages**: the existing page previews (`/api/previews`), drawn from the deck's SVG pages
  (resvg) or, from step 2 of decision 0012, through Office.
- **Layout**: a filmstrip of thumbnails, the selected slide large, its speaker notes below; slides
  this run changed are marked in the filmstrip.
- **Selecting a shape** reuses `PptxShapeOverlay`: Ask coscribe with the shape as a quote.
- **No preview** (a deck edited after its build, on a machine without Office): a text outline
  from `read_pptx`, slide by slide, with "Open in PowerPoint".

## 5. Excel

The Excel design (2026-10-15, section 5) dropped a preview panel on 2026-10-16. Two forms had
been looked at and neither was worth showing beside the chat. The grid comes back here because
the conditions differ:
- **On demand**: it is a panel the user opens, not something always beside the chat.
- **Selection**: it is how a range is selected and asked about.
- **This run's changes**: it shows the cells this run changed, which a picture of a printed page
  cannot.

- **Drawn by the app**:
  - values and formulas from the file; values computed by IronCalc when the file has none,
    as the tools already do;
  - fills, fonts, bold, number formats, column widths, row heights and merged cells;
  - sheet tabs, and a formula bar showing the selected cell's formula.
- **Charts and pictures**: a labelled box of their size with "Open in Excel". Drawing them is
  later work.
- **Size**: the route returns the used range up to 2,000 rows by 100 columns, and says when it
  cut.
- **Select and ask**: a range selection shows Sum, Average and Count in the status bar, and Ask
  coscribe sends the range address with its values as a quote.

## 6. Order and size

Each step is one PR of about 600 changed lines at most:

1. **This design and decision 0014.**
2. **Word review backend**: `read_docx_review`, `edit_docx_review`, the two routes, the rejected
   copy for the Original view; tests on generated files with threads and resolved comments.
3. **The viewer panel and Word review**: docx-preview, the rail, change controls, selection.
4. **PowerPoint in the viewer.**
5. **Excel in the viewer**: the route first, then the grid.

## 7. Risks

- **docx-preview's change and comment rendering is experimental.** The viewer checks its output
  against the backend's list and falls back to the rail without connectors (section 3).
- **Fidelity**: pages differ from Word's (no automatic pagination, substituted fonts). The
  viewer is for reading and reviewing; "Open in Word" is always one click away.
- **Comment threads** written by older Word versions have no `commentsExtended.xml`. Their
  replies then show as separate comments, as Word 2010 shows them.
- **Large files**: render time for a long document is not measured yet (step 3 measures it); a
  workbook beyond the limit shows its first part and says so.
