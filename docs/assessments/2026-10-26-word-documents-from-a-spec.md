# Design note: Word documents written from a spec, compiled onto a theme and checked (2026-10-26)

Design before code: it changes how every new Word document is written and read back. Status:
**proposed**, waiting for the maintainer's answers at the end. It rests on 0001 (a fixed, cached tool
list), 0012 (no LibreOffice), 0013 (a document style, not a script route), 0019 (the .docx is the
artifact) and 0020 (design systems are a library). It extends 0013 and 0019; it replaces neither.

## 摘要（中文）
- **问题**：模型写 Word 要么用脚本（版面好但不稳，预览靠猜，沙箱里还出错），要么用 `write_docx`（稳，但封面、KPI 卡片、提示框、带色表头这类版面设不了）。应用里的预览和编辑器只能“尽力渲染”任意 docx，永远追不上。
- **办法**：像 PPT 的 ppt-master 那样，把“写什么”和“怎么排”分开：①**计划**（短文档三行，长文档请你确认）→ ②**规格**（`write_docx` 的 `content` 从 Markdown 子集扩成“Markdown + 文档头 + 少量组件”，没有任何格式字段）→ ③**确定性编译**到真正的 Word 样式（主题来自设计系统库）→ ④**确定性检查**（不用模型）。
- **不推翻 0019**：docx 仍是唯一的真相，旁边不放源文件，你在 Word 里的改动照常有效。我们只限定“自己生成的 docx 只含编辑器能完整画出来的东西”，所以预览和编辑对它们是准的，由测试保证（读回来不出现锁定块）。
- **不改工具签名**（0001）：语法写在 Word skill 里，`write_docx` 的描述只加一行指向它。
- **数字只定义一次**：文档头里的 `facts` 写一次，正文、表格、图表引用它，检查器核对。这是针对“8.6 万 vs 6.7 万”这类自相矛盾。
- **脚本路线**：按 0013 仍不是写新文档的路线，只用于改别人的文件；组件补齐后，模型不再需要脚本去设封面分页、表头跨页重复这些。
- **门槛**：用现有 11 个 docx 评测任务加 3 个新任务，设计分不低于脚本路线（均值 4.2），检查器 0 条违规，数字矛盾 0。
- 分 6 步、每步不超过约 600 行，最后才切成默认。要你定的几件事在最后。

## 1. What is wrong now
- **Preview and edit chase the file.** The viewer and the editor draw whatever a .docx holds. A
  script-made document uses direct formatting, cover bars made of one-cell tables, drawn charts, tab
  leaders; each new shape shows wrong until someone teaches the renderer (#634 taught it tables, fills,
  charts and page size; the next document will bring others). That has no end.
- **Two routes, neither enough.** `write_docx` writes a markdown subset onto the house style
  (`tools/office/docx/_style.py`: fonts, headings, a table style, A4, a page-number footer) and is
  steady, but cannot make a cover, a row of KPI cards, a call-out, or a chart in the flow. A script
  can, and scored higher on design (4.17 and 4.26 against 3.91 and 3.70, `2026-10-16-word-quality.md`),
  but adds facts the sources do not give, costs 8–19% more, and in the product needs a Python and an
  approval per run (0013). In a real conversation the model still reached for a script to set a
  cover/contents page break and header repetition, and the script failed in the sandbox's temp folder.
- **Content contradicts itself.** A reviewer in that conversation found a total that was a simple sum
  of three overlapping channels, and a target above the member total: numbers typed in several places.

## 2. What we found elsewhere (2026-10-26)
- Claude's online Docs store a block structure (ids, hashes, a revision), have almost no styling
  (two font pairs), draw charts and diagrams as SVG from code, and export to Word, PDF and Markdown.
  Fidelity is never promised, so there is nothing to chase. It plans in the open: an outline of
  "pending" blocks first, filled one section at a time; a written brief before each chart; a
  fresh-eyes review at the end (read from its tool instructions, not its internals).
- `lhl/llm-teach-to-msword` ([legaldoc](https://github.com/lhl/llm-teach-to-msword)): the model
  fills a semantic IR with no formatting fields; layout is data read by a deterministic renderer and
  by a linter that reports 20 codes with locations (direct formatting, style inheritance resolved to
  `docDefaults`, fonts, margins, footer page numbers, heading order); the eval uses exact checks, no
  model judge (baseline 0.974). Two traps it names: Word theme attributes silently override explicit
  fonts and colours (the python-docx template has this), and text extraction must read `w:tab` and `w:br`.
- `json-to-office` and `openwebui-generate-documents` (both MIT): content separate from look, a theme
  compiled to real Word styles, a cover, call-outs, a contents field, live page numbers, native charts
  (the first). Neither previews. Neither is code we would adopt (`2026-10-21-docx-editing.md` rules out
  the AGPL editors for the same reason as before).
- Spec-driven development ([Böckeler on Fowler's site](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)):
  spec-first helps; the same workflow for every size is "a sledgehammer to crack a nut"; reviewing long
  markdown is worse than reviewing the result; agents ignore specs; regenerating from one spec is not
  deterministic. So: a plan whose weight follows the task, a spec that is parsed and checked (not only
  read), and no promise that the spec regenerates the document (the .docx stays the truth).
- Outlines and plans measurably help long text ([Writing Path](https://arxiv.org/html/2404.13919v1),
  [planning in one turn](https://arxiv.org/html/2410.06203v1)).
- Not found: a measurement of IR-and-render against script-written docx. Ours (0013's) is the nearest.

## 3. Design

### 3.1 Four steps, each cheaper than the one after
1. **Plan.** For a document of more than about three sections, or when the person asks, the model
   first writes a short plan in the conversation: who reads it, the one-sentence conclusion, the
   sections each with the component it will use, and the key figures (the `facts`). The person
   approves or revises through the plan UI that exists (`PLAN_CHOICE_*`). A short memo skips this;
   the plan is never a file the person must review. (Fowler's warning, taken as a rule.)
2. **Spec.** `write_docx(content=…)`, the tool's signature unchanged (0001). The content grammar grows:
   - a **document head** (YAML): `title`, `subtitle`, `author`, `date`, `design_system` (a library name,
     else the house style), `cover` (`band`, `rule`, `none`), `toc`, `header`, `footer`, and `facts:`
     (named values, each defined once);
   - the existing markdown subset (headings, lists, pipe tables, `[TOC]`, `{{comment:…}}`);
   - **components**, as fenced blocks (`:::callout warn … :::`): `cover`, `stats` (KPI cards: label,
     value, delta), `callout` (info, success, warn, danger), `chart` (kind and a data table, drawn as a
     native Word chart through the code `add_docx_chart` uses), `figure` (image, caption), `pagebreak`,
     `signature`. Eight at most; each added only when a task needs it.
   - **No formatting fields exist.** Colour, font, size, spacing and borders come from the theme.
     A value from `facts` is written `{fact:name}` and expanded at compile time.
3. **Compile** (deterministic): onto real Word styles (Normal, Title, Heading 1–3, Caption, Quote,
   Contents 1–3, List, a table style), the theme's fonts for Latin and East Asian text (set on the
   styles with the theme attributes removed, legaldoc's trap), A4 or the template's page, a real
   contents field, header and footer with PAGE fields, header row repeated and rows kept whole across
   pages, cover and contents on their own pages. Components become the same OOXML a person would build
   (one-cell shaded tables for bars, cards and call-outs) **with a marker** (a named bookmark or a table
   description) so the reader can tell what they were. `template_path` given: the template's styles
   win, as in 0013.
4. **Check** (deterministic, no model): the compile lints its own output and returns findings with
   locations to the model for one repair pass.
   - Format: direct formatting on a body run or paragraph, a theme attribute overriding a style, an
     empty paragraph used as a spacer, a heading level skipped, a table wider than the text area, an
     unknown style, a missing footer page number.
   - Readback: the file read as blocks (`read_doc_blocks`) holds **no locked block** and no table or
     picture the editor cannot draw. This is what makes the preview exact for these documents.
   - Facts: every `{fact:…}` is defined; every fact is used; a number in the prose that equals none of
     the facts or the table cells is listed (a hint, not an error); a chart's data equals its table's.
   - Layout that needs pagination (an empty page, a heading at the foot of a page) is not checked:
     there is no layout engine (0012). The editor and Review view do not claim it either.

### 3.2 Reading it back
0019 holds: the .docx is the artifact. The editor and Review view read what the compiler wrote like
any file (#634's look, tables, charts, page). New: the reader recognises the compiler's markers, so a
stats row or a call-out is shown as a component and its text can be edited in place, instead of a
read-only grid. A person who edits in Word keeps working: the markers are bookmarks and descriptions
that Word keeps, and the file is read again each time. (To verify on Word: that a save keeps them.)

### 3.3 The theme
A design system (0020) holds colours, fonts, text styles, spacing and radius for decks. Docs reads
the same system: colours and fonts become the theme; the text styles become Heading 1–3, Caption,
Quote; spacing becomes paragraph spacing; radius is unused. A document gets a copy, as a deck does.
No design system chosen: the house style that exists. 0020 left "how Docs uses a system" open; this
answers it for the compiler and leaves the picking UI for later.

### 3.4 The script route
Unchanged by this note: not the route for writing a document (0013); `run_python_script` stays for
reading and editing a user's own file. The components replace what the scripts were used for here.

## 4. Gate
- **Tasks**: the eleven in `office-agent/evals/docx/tasks` (01–11) plus three new: a report with cover,
  contents, a stats row, a chart and a shaded table (12); a document whose figures must agree across
  text, table and chart (13); the same report on a design system with a Chinese brand font (14).
- **Routes compared**: current main, the script route of `2026-10-16-word-quality.md`, the spec route.
- **To pass**: every existing check; design at least 4.2 on average and above current on 05, 06, 08, 10,
  12; content no lower; cost within 15% of current (the plan step costs tokens); the checker finds 0
  violations in every compiled document; 0 contradicting figures on 13. Exact checks decide; the
  blind judging is the second opinion, as before.
- Until it passes, `write_docx` keeps its current behaviour and the new grammar is opt-in by use.

## 5. Steps and size
1. Compiler: head, theme from the house style, cover, contents, callout, stats, figure, page breaks,
   header and footer; golden XML tests (about 600 lines, `tools/office/docx/`, no new dependency).
2. Native chart component through the existing chart code; the component markers (about 300).
3. The checker and the readback check, wired into `write_docx`'s result (about 400).
4. Docs reads a design system (colours, fonts, text styles) (about 300; touches `tools/design_systems.py`).
5. The gate: tasks 12–14, the three-way run, the Word skill text and the one-line docstring pointer
   (schema snapshot changes once, reviewed). Flip only if it passes.
6. The editor edits components in place; the plan step in the skill and UI.
`write_docx`'s description and the Word skill change in step 5, not before.

## 6. Risks
- **The grammar must stay small.** More than about eight components, or any formatting field, and the
  spec becomes the script again. A component is added only for a failing eval task.
- **Models write the grammar wrong.** The checker returns what is wrong with a location; one repair
  pass; a document that still fails is returned as a plain document with the findings listed.
- **Word is not here to verify.** Rendering of the compiled file in real Word on Windows is a manual
  check per step (`docs/manual-checks.md`); LibreOffice may be used in CI only to catch breakage.
- **Not deterministic.** Two runs from one plan differ; that is accepted, as the .docx, not the spec,
  is kept.
- **Plan ceremony.** Longer than a few lines, or required for a short document, and it fails Fowler's test.

## Not verified
- Whether Word keeps the component markers across a save; how the cheaper models write the grammar;
  the cost of the plan step; whether the design reaches 4.2 with eight components.

## Questions for the maintainer
1. **Grammar form.** Markdown with a YAML head and `:::` blocks (recommended: the model's usual surface,
   small review, `write_docx` unchanged) or a JSON spec (stricter, longer for the model to write)?
2. **Plan step.** A plan before documents of more than three sections, approved in the plan UI
   (recommended), or never required, only offered?
3. **Order.** Compiler and checker first with the editor unchanged (recommended), or the editor's
   component editing in the same pass?
4. **Design systems for Docs** in step 4 (recommended) or later, with the house style until then?
5. **Charts in the flow** as a native Word chart (recommended; the editor and Review draw it) or as an
   image (always drawn, not editable in Word)?
