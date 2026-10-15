# Excel: how to raise the quality of the workbooks coscribe makes

Research and measurements, 2026-10-15, done the same way as the PowerPoint work
(`2026-10-13-office-route.md`): what we have, what others do, a test of the route on our own
tasks, and a recommendation.

## 中文摘要

1. **现有评测测不出质量问题**：任务 01–08 每个单元格都写死了，测的是“照做”，基线全过（#181）。
   这次新增两个开放任务（09 销售分析报表、10 门店三年盈利预测），版面由模型决定，用“数字在任意单元格、
   公式数量、改假设后结果跟着变”来判对错，再用盲评打设计分。
2. **对照实验**：现有做法（`write_xlsx` 加十几次小工具调用拼表）对比“一次写出整本工作簿”
   （本地把 Excel skill 换成“用一个 openpyxl 脚本写整本，再 recalc 检查”，未提交）。两轮、各 4 个任务、
   盲评 3 次：
   - 开放任务和带图任务，设计分 **3.0 → 4.1**（满分 5），8 次对比全部胜出；
   - 正确性两边都全对；
   - 花费和时间持平（4 个任务约 0.5–0.7 元，9–12 分钟）。
   - 照做类任务（01–08）基本持平：07 更好，03（在用户的表里加列）更差，新列没跟原表样式。
3. **结论**：杠杆和 PPT 一样，是“整份一次写出”，而不是更多规则。但产品里不能走脚本：
   - 桌面版跑脚本需要用户电脑装 Python，首次还要 pip 下载包；
   - 每次运行都要用户批准（EXEC）。
4. **建议**：做一个 `build_xlsx` 工具，从一份完整的工作簿描述（JSON：表、单元格、公式、样式、列宽、图表、
   打印设置）确定性地生成 .xlsx，接着自动重算和检查。这就是 PPT 的 `build_pptx_from_pages`
   在 Excel 上的对应物，安装包不增大（openpyxl 已在包里）。编辑用户已有的表，仍用现有的小工具。
5. **两种做法都有的缺陷，交给检查器**：
   - 打印时图表、列被切到另一页；
   - 文字被截断，合计显示成 `###`；
   - 加的新列没沿用原表样式。
6. **外部调研**：
   - SpreadsheetBench（真实论坛问题）上，微软 Excel Agent Mode 57.2%，人类 71.3%。它的做法是先读工作簿“蓝图”，每步都验证；
   - 开源的 Excel 工具基本都基于 openpyxl，没有可以直接搬来提升质量的引擎；
   - 公式引擎和透视表等，等真实需求出现再说。

## 1. What coscribe has

- **Tools**:
  - `write_xlsx` writes one sheet from a pipe table, sizes its columns, recalculates through
    LibreOffice and reports formula errors;
  - small tools for the rest: `edit_xlsx_cells`, `format_xlsx_cells`, `add_xlsx_chart`,
    `add_xlsx_conditional_format`, `recalc_xlsx`, `read_xlsx`, column widths, freeze panes,
    validation lists.

  Most of them are deferred, so each costs a `use_tool` round.
- **Skill**: `builtin_skills/excel/SKILL.md` (3.5 KB): formulas over numbers, financial-model
  colours and formats, verify after recalculating.
- **Evaluation**:
  - before this work: eight tasks, each naming every cell;
  - the baseline (#181) passed every value, formula and probe check, with design scores of
    3.6–4.0, and the column-width defect it found was fixed (#193).

  Such tasks measure following instructions, not making a good workbook, so they could not show
  where quality is lost.

## 2. Outside routes (checked 2026-10-15)

| What | Licence | What it tells us |
|---|---|---|
| SpreadsheetBench | CC BY-SA 4.0 | 912 real forum questions on real workbooks, a Verified set of 400; the standard correctness benchmark |
| Microsoft Excel Agent Mode | product | 57.2% on SpreadsheetBench (people 71.3%); reads a "blueprint" of the workbook (layout, values, formula dependencies) and verifies every step |
| Shortcut.ai | product | 46.6% on the same benchmark |
| excel-mcp-server, Bread_Excel_Agent (110 atomic tools) | MIT / open | openpyxl underneath, many small tools: the route coscribe has now |
| OfficeCLI | Apache-2.0, .NET | 350+ functions, pivot tables, dynamic arrays; a .NET binary, not code we can own in Python |
| GenOffice | Apache-2.0 | Univer and a Rust sidecar (calamine, IronCalc); a different stack |
| xlsx-evaluate | MIT | a Python formula evaluator (fork of xlcalculator); pycel is archived |
| Anthropic's xlsx skill | proprietary | ideas only: openpyxl script, LibreOffice recalc, a zero-formula-error rule, colour conventions; coscribe's skill already has these |

### 2.1 How the products write a workbook

**Claude for Excel** (Anthropic's add-in). Anthropic has not published its tools; this
comes from a third party's reverse-engineering notes (`hewliyang/reversing`,
`claude-for-excel/`), so it is unverified and may have changed. Ideas only, no text copied.
- **Size of the tool set**: about a dozen coarse tools.
  - Reads: sheet metadata, ranges, CSV, search, objects.
  - Writes: a block of cells, clear, copy a pattern, rows and columns, sheets, resize, and
    `modify_object` for charts and pivot tables.
  - An Office.js escape hatch, and a Python container for large data, which calls the read
    and write tools from code.
- **The main write tool, `set_cell_range`**, writes a rectangular block in one call.
  - Each cell carries a value or a formula, a note, font, fill, alignment, number format and
    borders.
  - `copyToRange` repeats a pattern down a column.
  - Nothing is overwritten without being asked.
  - It returns the computed value of every formula it wrote, so a wrong one shows at once.
- **Charts** take a contiguous source range and an anchor cell.
- **Context**: the first message carries the workbook's sheets with their sizes and frozen
  panes; every message carries the active sheet and the selection.
- **Its rules**:
  - formulas over computed numbers;
  - assumptions in their own cells;
  - the finance colours;
  - when editing, copy the format of a neighbouring cell (which is task 03's defect);
  - for a big task, plan, check at milestones, then review references, errors and formats
    at the end.

**Microsoft Excel Agent Mode**:
- a "Document Context Producer" sends a compact blueprint of the workbook (layout, values,
  objects, formula dependencies), and the agent asks for more when it needs it;
- a plan, act, check loop that runs light tests before each action and writes through
  Office.js.

**Shortcut** (self-reported): planning, execution and verification agents, and its own
spreadsheet engine so it can create .xlsx files without Excel.

**Research and open source**:
- **SheetBrain** (Microsoft, MIT, AAAI 2026): understand, then execute in a Python sandbox,
  then validate and retry. It is aimed at analysis questions, not at building a workbook.
- **sv-excel-agent** (MIT): about 30 MCP tools, scored on a 50-task SpreadsheetBench subset.
  It notes that LibreOffice recalculates less faithfully than Excel, so its scores can differ.
- **opensheets** (MIT): an Excel and Google Sheets add-in, with little documentation.

What they share:
- the model writes a whole block of cells, styles included, in one call, not a value call
  followed by format calls;
- every write returns its computed results;
- the workbook's shape is given to the model before it starts;
- an edit copies the format around it.

coscribe's `write_xlsx` takes values only, so styling one table costs 5–20 more calls, which
is where the current route's 26–59 calls come from.

There is no engine to take over. The open projects use openpyxl as we do. The best product
gains from reading the workbook first and verifying each step, which coscribe already does
(`write_xlsx` recalculates and reports errors). So the open question is how the model writes
a workbook, not what writes the file.

## 3. Method

- **Two open tasks** (`evals/xlsx/tasks/09-sales-report`, `10-store-forecast`), with the
  layout left to the model:
  - **09**: a 480-line sales ledger, made reproducibly by `make_inputs.py`. The brief asks
    for a report for the boss: by region, by product line, the monthly trend, a chart,
    totals as formulas.
  - **10**: a three-year forecast for five stores from seven assumptions; the assumptions
    must be separate and editable.
- **New checks**, all deterministic:
  - `figures`: the totals appear in some cell, in yuan, thousands or 万;
  - `formulas_min`: a minimum number of formula cells;
  - `input_probe`: the cell holding the 8% growth is found by its value and set to 10% on a
    copy; after recalculating, net profit must be 369 万 and 477.9 万 in years 2 and 3. A
    workbook of pasted numbers fails it, which a reference solution test shows.
- **Two routes**, both with DeepSeek at effort low and the same tools:
  - **current**: the skill as it is;
  - **script**: the skill replaced locally (not committed) by one that says to build a new
    workbook in one `run_python_script` with openpyxl, then `recalc_xlsx`, and to keep the
    small tools for small edits.
- **Runs and judging**:
  - round 1 and round 2 each ran both routes on tasks 02, 04, 09 and 10; the script route also
    ran all ten tasks once;
  - a blind judge (DeepSeek, 3 rounds) scored the printed pages of the two routes side by side.

## 4. Findings

### 4.1 Correctness is not where quality is lost

Every run of both routes passed every deterministic check on all ten tasks:
- values, formulas and probes;
- the new figures, formula count and input probe.

There were two exceptions:
- task 09 had one cut-off label on both routes;
- the script route's task 01 failed the date format, because the check read `yyyy\-mm\-dd` as
  different from `yyyy-mm-dd`. That was the check being too strict, and it is fixed: an
  escaped literal now matches.

### 4.2 Writing the whole workbook at once scores higher on design

Design score out of 5, the mean of three blind rounds (content and coherence moved the same way):

| task | current, r1 | script, r1 | current, r2 | script, r2 |
|---|---|---|---|---|
| 02 monthly summary | 2.33 | 4.77 | 2.80 | 4.47 |
| 04 line chart | 2.93 | 4.00 | 3.17 | 4.33 |
| 09 sales report | 3.00 | 4.07 | 3.40 | 3.83 |
| 10 store forecast | 2.83 | 3.60 | 3.50 | 3.77 |
| **mean** | **2.77** | **4.11** | **3.22** | **4.10** |

The script route won all 8 comparisons. What the judge saw:
- on the current route, charts split across printed pages, a column torn off from its labels,
  and totals printing as `###` (task 02, round 1);
- on the script route, a summary sheet with headline figures, three tables and three charts
  (task 09), and the inputs in blue.

The current route assembles a workbook in 26–59 calls (one round each for writing, formatting,
widths, a chart and freezing), so no single step sees the whole page. The script route lays it
out in one place.

On the eight instruction tasks (01–08) the two routes are level:

| | current | script |
|---|---|---|
| design, mean of 6 tasks | 4.12 | 4.10 |

- 07 (Chinese formats) went from 3.37 to 4.40.
- 03 (add columns to a user's sheet) went from 4.17 to 3.17: the new columns did not take
  the existing header style or number format.

### 4.3 Cost and time are level

| tasks 02, 04, 09, 10 | yuan | minutes |
|---|---|---|
| current, r1 / r2 | 0.60 / 0.66 | 12.4 / 11.5 |
| script, r1 / r2 | 0.51 / 0.67 | 9.4 / 12.6 |

All ten tasks: 1.00 yuan (current) and 1.06 yuan (script). Most of the cost is task 09, about
0.25–0.37 yuan.

### 4.4 Why the product cannot simply switch to scripts

`run_python_script` is an EXEC tool:
- in the app each run waits for the user's approval; the evaluation approves automatically;
- in the desktop build it needs a Python on the user's machine;
- on first use it installs openpyxl and pandas from PyPI (`tools/script_env.py`).

A user without Python gets an error instead of a workbook. The gain is in writing the workbook
whole, and that does not need a script: a declarative description of the whole workbook,
compiled in-process, gives the same single view without exec, approvals or a Python on the
machine. This is decision 0010's principle (office files are compiled from whole-page
sources), applied to Excel.

### 4.5 Defects left on both routes

These are for a checker, as on PowerPoint:
- **print layout**: a chart or a column splits across pages. The judge reads the printed
  pages, which weighs this more than a reader on screen would; a boss's report is still
  printed or sent as a PDF.
- **clipped text** and `###` totals: the `legibility` check finds them after the fact; the
  build should catch them before the user sees them.
- **edits that ignore the sheet's style**: a new column next to styled ones must copy their
  header and number format.

### 4.6 Smaller findings

- The evaluation's `tool_seconds` pairs a tool's start and result by name, and some tools'
  times are wrong: 103 s for `read_xlsx` and 171 s for `task_update`, which are instant. The
  totals per task (`wall_seconds`) are right. To fix in the recorder.

## 5. Recommendation

1. **`build_xlsx(path, spec)`**, a WRITE_LOCAL tool, compiles a whole-workbook spec in one call
   with openpyxl, then recalculates and checks it.
   - **The spec**: sheets made of blocks, as in Claude for Excel's `set_cell_range`:
     - an anchor cell and rows of cells, each a value or a formula;
     - a style per cell or per block, named once and referenced, or copied from a
       neighbouring cell;
     - a pattern repeated down a column.

     Then widths, merges, freeze panes, charts given by source range and anchor, conditional
     formats, validation lists and print setup.
   - **The result** returns the computed value of each formula after LibreOffice
     recalculates, so a wrong number shows in the same round.
   - **The result** names errors by cell: formula errors, `###`, clipped text, a chart over
     cells or across a page break, and a typed number where its row is formulas.
   - A user's workbook that is being reshaped (new sheets, a report built on its data) gets
     the same tool with `base: <file>`, so its existing sheets are kept.
   - Small edits keep the current tools.
2. **The skill** says to plan the layout first (summary in front, data behind, assumptions in
   one block) and to write the workbook in one `build_xlsx` call, with one repair call if
   needed. Its formula and format rules stay.
3. **Measure it** against the two runs here, on the ten tasks:
   - the bar is a design mean of about 4.1 on 02, 04, 09 and 10, with the cost level;
   - task 03 must not fall.
4. **Later, only if a real case asks**:
   - a sample of SpreadsheetBench Verified for correctness on real questions. Its CC BY-SA
     licence means the task files are fetched by a script, not committed;
   - pivot tables;
   - dynamic-array functions.

The engine underneath, decided with the maintainer on 2026-10-15, comes in stages behind one
tool interface:

1. **openpyxl and LibreOffice**: works with no Excel installed, which is the baseline every
   user gets.
2. **Real Excel through COM** on Windows when it is installed: Excel recalculates and saves,
   so charts, pivot tables and slicers survive as they do in Claude for Excel. It falls back
   to stage 1 when Excel is missing.
3. **An Excel add-in (Office.js)**: a task-pane page that is coscribe's hands inside Excel,
   working on the open workbook. The local server stays the brain: model, tools, approvals.

Stages 2 and 3 are chosen from real use after stage 1 ships. The block interface is what
carries over to all three.

Size: the tool and its checks are about 500–700 lines with tests, in `tools/office/xlsx/`, and
the installer does not grow. It lands as two PRs:
- part 1: the tool, not yet offered to the model;
- part 2: the skill switches to it, with the measurement.

## 6. Not verified

- The workbooks in Excel on Windows: the judge saw LibreOffice's printed pages. The fonts and
  page breaks there can differ from Excel's.
- Whether a spec tool keeps the script route's gain: that is what step 3 measures.
- Two runs per route on four tasks, judged by one model (DeepSeek). The gap was the same in
  both rounds and on every task, but a second judge (Gemini, free tier) was not used.
