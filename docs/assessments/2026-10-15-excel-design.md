# Excel: the design of workbook writing, its engines and the preview

Design, 2026-10-15. It follows the research in `2026-10-15-excel-quality.md` and is recorded as
decision 0011, accepted by the maintainer with the three open choices decided as recommended.

## 中文摘要

**核心决定：一套“操作清单”接口，三种执行底层。**

1. **接口（第 1 步，现在做）：** 模型交一份操作清单，程序执行，然后自动重算、检查、返回结果。
   - 操作的形状对齐 Claude for Excel：写一块单元格（值或公式、样式、批注、向下复制）；
     改结构（插删行列、建表、冻结、列宽）；建对象（图表、条件格式、数据验证、打印设置）。
   - 一次调用可以只写一块，也可以写整本，评测里测出的“一次写出”的好处就保住了。
   - 每个操作都能一一翻译成 openpyxl、Excel COM、Office.js，三种底层共用这一份接口。
   - 用 2 个新工具替代现在 10 个零碎的写入工具：
     - `write_xlsx_cells`：写块；
     - `modify_xlsx`：结构和对象。
   - 读的一侧，`read_xlsx` 增加“工作簿概览”：类似微软的蓝图，给出各表区域、公式模式、
     命名、图表、透视表，以及修改时可能丢失的功能。
   - DeepSeek 会把所有工具一次性全部发给模型，工具定义变短，每次请求都省。
2. **保真度（实测）：** 两条现有路径都不是无损的。
   - **openpyxl 读写一遍：** 丢迷你图、2010 版条件格式扩展、所有公式缓存值。
   - **LibreOffice 重存：** 保住了这些，但丢了一处工作表标签颜色，还会改写样式。

   因此：
   - 改用户的表时，先检查有没有会丢的功能；有就不改原文件，说明会丢什么，改为写一份副本。
     这和 Claude for Excel 的“不覆盖”保护是同一个思路。
   - 用户的原文件不再交给 LibreOffice 原地重存，只在副本上重算，用来出结果、检查和预览；
     交付的文件标记“打开时重算”。
   - 新建的工作簿照旧重存，这样数值在任何查看器里都能显示。
3. **检查器：** 结果里按单元格列出问题：
   - 公式错误，`###`，文字被截断；
   - 一行公式中夹了手填数字；
   - 图表盖住数据，打印时被分页；
   - 新加的单元格没沿用旁边的样式；
   - 会丢的功能。

   和 PPT 一样，最多两轮修复。
4. **预览面板（第 1 步之后）：** 在 coscribe 里直接看表，不用打开 Excel。
   - 用 LibreOffice 导出 HTML（实测 1.8 秒）：带格式的表格，图表转成图片，可切换工作表；
   - 每次写入后自动刷新。
5. **第 2 步，真 Excel（COM）：** 建议先于加载项做。
   - 它可以连上用户正开着的 Excel、直接改那本表，实时可见，体验接近加载项；
   - 不需要证书和部署。
   - 只能在装了 Excel 的 Windows 上用，其他情况自动回到第 1 步。
6. **第 3 步，加载项（Office.js）：** 列为待验证项。
   - 正式部署只能由公司 IT 通过 Microsoft 365 管理中心统一推送，或上架微软商店；共享文件夹方式只能用于测试；
   - 页面必须走受信任的 HTTPS，连本机 coscribe 还涉及证书和浏览器的本地网络限制；
   - Claude for Excel 靠云端后台绕开了这些，coscribe 是本地程序，这里最难。
   - 先做一次小验证，再决定做不做。
7. **门槛：**
   - 第二部分在任务 01–10 上，02/04/09/10 的设计分达到约 4.0（脚本路线 4.1）；
   - 花费不高于现在，正确性不降，任务 03 不低于 4.17；
   - 新增两个任务：一本带丰富功能的用户表（测“不丢东西”），一份 5000 行的数据（测大数据）。

**已定（维护者，2026-10-15）：**
- 改过的用户原文件不再由 LibreOffice 重存；
- 达标后删掉旧的 10 个写入工具；
- 第 2 步先做 COM，加载项后议。

原先列出的 3 件事：
- 交付给用户的、改过的原文件，是否不再由 LibreOffice 重存？建议不再重存。
- 第二部分评测达标后，是否删掉旧的 10 个写入工具？建议删。
- 第 2 步是否先做 COM、加载项后议？建议是。

## 1. What decides the design

- **Measured**:
  - a workbook written whole scored 4.1 against 2.8–3.2, at the same cost;
  - the many-small-tools route spends 26–59 calls a task, most of them styling.
- **Mainstream products**: Claude for Excel and Microsoft Agent Mode both
  - write a block of cells (values or formulas with styles) per call;
  - return computed results;
  - give the model the workbook's shape first;
  - copy the format around an edit;
  - refuse to overwrite silently.
- **Constraints**:
  - it works without Excel;
  - no exec or approval for writing a workbook;
  - the installer does not grow;
  - the tool list is fixed and cached (0001); DeepSeek binds every built-in tool up front,
    so fewer and shorter schemas help every request;
  - Windows only.
- **Fidelity, measured here** on a workbook made with xlsxwriter (a table, sparklines, a data
  bar, a colour scale, a validation, a comment, a link, freeze panes, merges, fit-to-page, a
  header, a styled chart, an image, a defined name, sheet protection, a tab colour):

  | feature | openpyxl load and save | LibreOffice recalc (resaves in place) |
  |---|---|---|
  | sparklines | **lost** | kept |
  | data bar's Excel 2010 extension | **lost** | kept |
  | cached formula values | **lost** (Excel recalculates on open; previews show blanks) | written |
  | tab colour | kept | **lost** |
  | styles | kept | rewritten (equivalent so far, `test_a_workbook_that_libreoffice_resaved_keeps_the_styles_the_check_compares`) |
  | table, validation, conditional formats, comment, link, freeze, merges, print setup, chart and its colours, image, name, protection | kept | kept |

  openpyxl also warns, while loading, about every extension it will drop. That warning is the
  signal the guard below uses. Pivot tables, slicers, timelines and form controls were not in
  this workbook: they could not be made here without Excel, and are to be checked on Windows.

## 2. The interface: an operation list

One schema, engine-neutral: every operation maps to one openpyxl call, one Excel COM call and
one Office.js call. Two writing tools take a list of operations, so the model writes one block
or a whole workbook in a call.

**`write_xlsx_cells(path, blocks, overwrite=false)`**

A block is:
- `sheet`: created if missing;
- `at`: the top-left cell;
- `rows`: rows of cells. A cell is a number, text, `=formula`, or an object
  `{v | f, style, note}`;
- `style`: the block's default, a named style or inline fields: `bold`, `italic`, `color`,
  `fill`, `align`, `wrap`, `num` (number format), `border`, `font`, `size`;
- `styles`: named styles, defined once per call;
- `like`: copy the style of a neighbouring cell or row, which is what an edit beside an
  existing table uses;
- `fill_down`: repeat the last row's formulas to a row.

The result:
- the computed value of every formula written (capped; the rest summarised as counts);
- errors by cell;
- the checker's findings (section 4).

Writing over non-empty cells without `overwrite` is refused, and the refusal names what is
there.

**`modify_xlsx(path, ops)`**, where an op is one of:
- `sheet`: add, rename, delete, move, tab colour;
- `rows` / `cols`: insert, delete, width, height, hide, group;
- `freeze`, `merge`;
- `chart`: kind, source range, anchor, title, axis titles, series colours, size;
- `conditional`: rule, range, colours;
- `validation`: list or range, cells;
- `print`: orientation, fit to width, repeat header rows, area;
- `name`: a defined name.

Charts take a source range and an anchor cell, as in Claude for Excel; the source's first row
gives series names and its first column the categories.

**Reading.** `read_xlsx` gains an overview, which is the default for a workbook over a size:
- each sheet's used range, header rows and tables;
- the formula regions in R1C1 form (`D2:D13 = RC[-2]-RC[-1]`);
- names, charts, pivot tables and validations;
- what an edit would lose.

Cell ranges are read on request, as now. It is a tool result, never the system prompt (0001).

**What it replaces.** After part 1b meets its gate, these ten tools go:
`write_xlsx`, `format_xlsx_cells`, `edit_xlsx_cells`, `merge_xlsx_cells`,
`unmerge_xlsx_cells`, `add_xlsx_chart`, `add_xlsx_conditional_format`,
`set_xlsx_data_validation`, `freeze_xlsx_panes`, `set_xlsx_column_width`.
`read_xlsx` and `recalc_xlsx` stay. `run_python_script` stays for analysis (pandas over
thousands of rows); the skill says results go into the workbook as formulas through the
tools.

## 3. Engine, recalculation and fidelity in stage 1

- **New workbook**: openpyxl writes it. LibreOffice recalculates it and resaves it in place,
  as today, so every viewer shows numbers.
- **A user's workbook**:
  - **The guard**: before writing, load it and collect openpyxl's "will be removed" warnings,
    plus parts openpyxl does not keep (`vbaProject.bin` unless .xlsm with `keep_vba`, slicers,
    timelines, external links, form controls).
  - If any are found, the original is not touched. The tool writes `<name> (coscribe).xlsx`
    and says what that copy lacks; with Excel present (stage 2) the edit goes through Excel
    instead.
  - **No resave of the original**: the delivered file is openpyxl's output with
    `fullCalcOnLoad`. LibreOffice recalculates a copy, and the results, checks and preview
    come from that copy. Excel, WPS and LibreOffice recalculate on open.
  - **Open question for Windows**: whether Explorer's and Outlook's preview panes show
    numbers for such a file.
- XLOOKUP/XMATCH keep coscribe's own evaluator; dynamic arrays stay out of scope.

## 4. The checker

It is run after every write on the recalculated copy. Each finding names a cell, as the deck
checker names a page:
- formula errors;
- `###`, and text cut off by the next cell (moved from the evaluation, `clipped_texts`);
- a typed number inside a row or column of formulas (the pattern break);
- a chart over non-empty cells;
- a chart or a table crossing a printed page boundary, for sheets with a print area or fit
  settings, measured from LibreOffice's PDF page breaks;
- a new cell beside a styled table without its style;
- the guard's losses.

After two repair rounds the result says to stop repairing, as decks do. Findings the model
cannot act on are not reported.

## 5. The preview panel (after part 2)

- **Source**: LibreOffice's HTML export of the recalculated copy. Measured at 1.8 s for two
  sheets; each sheet becomes a table with formatted values (`¥1,000`) and its charts become
  images.
- **Panel**:
  - shown beside the chat for the workbook the last tool wrote;
  - sheet tabs;
  - refreshed after each write;
  - "Open in Excel" uses the existing `open_in_os`.
- **Later**: clicking a cell shows its formula, from the overview data, not the HTML.

## 6. Stage 2: real Excel through COM

- **The same operations**, executed by Excel in a worker thread. COM calls must stay on one
  thread.
- **Attaching**: when the target workbook is open in the user's Excel, the engine attaches
  and edits it there, live, as the add-in would. Otherwise it opens a hidden instance.
- **Results**: Excel recalculates and saves, so nothing is lost, and the computed values come
  from Excel.
- **Library**:
  - pywin32 is BSD-style and adds native files;
  - comtypes is pure Python (licence to be checked);
  - xlwings (BSD-3) is built on both.

  The choice is made by installer size, which must not grow noticeably.
- **Falls back** to stage 1 when Excel is missing or COM fails.
- **Tested** in the Windows CI job only if a runner has Excel, which GitHub's hosted runners
  do not. Otherwise the maintainer checks a script of operations on a real machine.

## 7. Stage 3: an Office.js add-in, to be proven first

**Facts** (Microsoft Learn, 2026-06):
- a task-pane add-in needs a manifest;
- production deployment is the Microsoft 365 admin centre (an organisation's IT) or the
  Marketplace; the shared-folder catalog is for testing only;
- pages must be HTTPS, and a self-signed certificate is accepted for development only when
  the machine trusts it.

**Open**:
- how a production add-in served over trusted HTTPS reaches the local server (certificate,
  Chromium's private-network rules);
- whether Bosch IT would deploy it.

Claude for Excel avoids both with a cloud backend; coscribe is local, so this is the hard
part. The plan is a one-week spike, and a decision after it. The operations from section 2
would be its executor's protocol.

## 8. Plan, gates and size

| part | what | size | gate |
|---|---|---|---|
| 1a | the operation schema, the openpyxl executor, the guard, the checker; not offered to the model | ~700 lines with tests | unit tests; the reference solutions of tasks 01–10 rebuilt through it pass every check |
| 1b | the tools registered, `read_xlsx` overview, the skill, the coordinator text (invariant path: independent review) | ~300 lines | tasks 01–10 off-peak, two rounds: design ≥ about 4.0 on 02/04/09/10, cost ≤ current, every check as before, task 03 ≥ 4.17 |
| 1c | two new tasks (a rich user workbook: nothing lost or a copy with the losses named; 5,000 rows: formulas, not pasted numbers), then removing the ten tools | ~200 lines | the same runs |
| 1d | the preview panel | frontend | the maintainer looks at it |
| 2 | the COM engine | after real use | the maintainer's Windows check |
| 3 | the add-in spike | after 2 | a written decision |

If 1b misses its gate, the fallback measured in the research is a skill that writes whole
blocks through the same tools. A gap that remains is the evidence for the next change, as
with decks.

## 9. Risks

- **Large JSON blocks**: a model writing 500 rows as JSON spends output tokens. For a big
  table, the block takes a CSV file path or a range copied from another file instead of
  rows: `{"from_csv": "data.csv"}`.
- **Schema size**: two tools with nested operations must stay smaller than the ten they
  replace. This is measured in `tests/tool_schemas.txt` before 1b merges.
- **Not delivering LibreOffice's resave** of user files changes what viewers without a
  calculation engine show. This is to be checked on Windows (section 3).
- **COM**: Excel dialogs, a locked file, and the user typing while the engine edits. Each
  needs handling, and only a real machine shows them.
