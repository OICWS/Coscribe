# Word: how to raise the quality of the documents coscribe makes

Measurements, 2026-10-16, done the same way as the Excel work (`2026-10-15-excel-quality.md`):
what we have, a test of a second route on our own tasks, and a recommendation. The outside routes
for Word were surveyed in `2026-10-13-office-route.md` (section 5) and are not repeated here.

## 中文摘要

1. **评测先补开放任务**：任务 01–08 都写明了版面，测的是“照做”。新增 09（给客户的方案）和
   10（给管理层的中文半年总结），版面由模型决定（#324）。
2. **对照实验**：现有做法（`write_docx` 写 markdown 子集，再用编辑工具改）对比“一个 python-docx
   脚本写出整份文档，连同样式”（本地替换 Word skill，未提交）。10 个任务、两轮、每轮盲评 3 次：
   - 确定性检查两边几乎全过（事实 100%）；脚本路线第二轮 06 漏了一个要求的标题；
   - 设计分：现有 3.91 / 3.70，脚本 4.17 / 4.26（满分 5）；
   - 内容和连贯持平；
   - 脚本路线贵 8–19%，慢约 35%。
3. **差距集中在几类任务**，两轮都赢：05 数据表（+0.87 / +1.80）、06 中英混排（+1.03 / +1.53）、
   08 图片加图注、10 半年总结。评审对现有路线的意见每次一样：表头没有底色、表格像贴进来的
   电子表格、字体和间距平淡。这些是现有工具设不了的。
4. **脚本路线也有稳定的缺点**：01 两轮内容都输（−0.93 / −1.37），每次都加了笔记里没有的副标题和
   参会人、把“预留预算”放进成本表、把“下一步”单独留在几乎空白的第二页。整份自己写时，它会加料。
5. **结论**：Word 缺的是版式能力，不是写法。产品里也不能走脚本（需要用户电脑装 Python，每次运行
   要批准）。
6. **建议**：保留 `write_docx` 和编辑工具，给它加一个文档样式：正文和中文字体、标题样式、强调色、
   表格样式（表头底色、合计行加粗）、页脚页码；不传时用一套默认样式，传模板时模板优先。
   做完后用这两轮当基线再测。

## 1. What coscribe has

- **Tools**:
  - `write_docx` writes a whole document from a markdown subset (headings, lists, pipe tables,
    `[TOC]`, `{{comment: ...}}`), on a template's styles when one is given, optionally as tracked
    changes;
  - edits that leave the rest of the file alone: `replace_docx_text`, `insert_docx_text`,
    `delete_docx_text`, `add_docx_chart` (a native chart), `add_docx_image`.
- **What `write_docx` sets on its own**: tables in the `Table Grid` style, sized to the page, a
  bold header row repeated on each page, numeric columns right-aligned, table text at 10 or 9 pt
  when the body is larger. Everything else comes from python-docx's blank document or the
  template.
- **What it cannot set**: fonts (no East Asian font, so Chinese falls back to whatever Word picks),
  heading look, an accent colour, a shaded table header or an emphasised total row, a header or a
  footer with page numbers.
- **Skill**: `builtin_skills/word/SKILL.md` (3.7 KB): the TOC, comments against tracked changes,
  templates, charts and pictures.

## 2. The test

- **Tasks**: the eight instruction-following tasks (01–08), plus the two open ones (09, 10).
- **Route `current`**: main as it is.
- **Route `script`**: the Word skill replaced, locally and uncommitted, by one that says to write a
  new document whole in one `run_python_script` with python-docx, styles first, then to check it
  with `read_docx` and `review_work`; editing a user's document keeps the edit tools. Its rules are
  in the appendix.
- **Runs**: DeepSeek flash at low effort, off-peak; two rounds of both routes; each document judged
  blind three times on design, content and coherence (1–5), with both routes' documents in the
  same judging run.

## 3. Results

Every deterministic check passed in all four runs (facts, headings, contents list, tables, images
and captions, tracked changes, template, no markdown left), with one exception: in the script
route's second run, task 06 dropped the required heading "入职".

| | current r1 | script r1 | current r2 | script r2 |
|---|---|---|---|---|
| Design | 3.91 | 4.17 | 3.70 | 4.26 |
| Content | 4.29 | 4.23 | 4.19 | 4.28 |
| Coherence | 4.24 | 4.21 | 4.18 | 4.35 |
| Cost, 10 tasks (yuan) | 0.88 | 0.95 | 0.83 | 0.99 |
| Task time, summed (s) | 975 | 1,331 | 1,241 | 1,664 |

Design by task, script minus current:

| Task | r1 | r2 | |
|---|---|---|---|
| 01 report from notes | +0.07 | −0.40 | content −0.93 / −1.37 |
| 02 memo from a PDF | +0.77 | −0.47 | flips |
| 03 tracked contract | +0.27 | 0.00 | |
| 04 letter on a template | +0.10 | 0.00 | the template decides |
| 05 table-heavy | +0.87 | +1.80 | |
| 06 mixed Chinese and English | +1.03 | +1.53 | |
| 07 restructure a manual | −0.70 | +0.43 | flips |
| 08 image with caption | +0.17 | +0.70 | |
| 09 proposal (open) | −0.13 | +0.90 | |
| 10 half-year summary (open) | +0.20 | +1.10 | |

How to read it:
- **Noise is large.** The same route on the same task moved by up to 0.76 between rounds (current
  05: 3.63 then 2.87; current 02: 3.70 then 4.30). Only a gap that repeats counts.
- **What repeats is layout.** 05, 06, 08 and 10 go the script route's way in both rounds. The
  judges' notes on the current route's documents say the same things each time: the table header
  has no fill, the table "reads as a bare spreadsheet dump", the title is "a small plain blue
  line", spacing is flat. On 06 the Chinese text has no East Asian font set.
- **Where the template or the user's document decides the look** (03, 04, 07), the routes are
  level, as expected: both edit or restyle onto what is there.
- **The script route adds things.** On 01, in both rounds, it added a subtitle naming attendees and
  roles the notes do not give, put a "budget set aside" row into a costs-only table, and left
  "Next steps" alone on a nearly blank second page. Writing every byte of the document itself
  gives the model more room to embellish as well as to style.
- **Cost and time**: the script route costs 8–19% more and takes about 35% longer (a script to
  write, run, read back and often fix).

## 4. Recommendation

The gap is in what `write_docx` can express, not in writing the document whole: `write_docx`
already writes a whole document from one source, as decision 0010 asks. A script route would also
need a Python on the user's machine and an approval for every run (the reason Excel did not take
it either, decision 0011).

So `write_docx` gains a **document style** (#325), compiled onto real Word styles so the user can keep
editing (Normal, Title, Heading 1–3, a table style), not onto direct formatting:
- body font for Latin and East Asian text, size, line and paragraph spacing;
- heading font, sizes and an accent colour, used for headings and the table header;
- tables: a shaded, bold header row; a bold total row (first cell "Total", "合计" and the like);
  numbers right-aligned (as now);
- page: a footer with the page number (a PAGE field), an optional header line.

Without a style the document gets a default house style, so a model that picks nothing still gets
the better layout. With `template_path`, the template's styles win and nothing is overridden. The
edit tools stay. The Word skill gets the few rules from the script route that are not about
python-docx (who reads it; a first page that says what it is; tables for figures a reader
compares; add nothing that is not in the sources).

**Gate** for the change, on the same ten tasks, two rounds: every check passes as now; design at
least the script route's (4.2 on average) and above the current route's on 05, 06, 08 and 10;
content no lower; cost within 10% of the current route.

## Appendix: the script route's rules (uncommitted skill)

- Styles before text: the Normal font and size once (for Chinese also the East Asian font), line
  and paragraph spacing; Title, Heading 1 and Heading 2 defined and used for every heading.
- Page: A4 unless the reader is American; margins; a footer with the page number; a header with
  the short title where it helps.
- A first page that says what it is: title, for whom, date, the point in two lines.
- Tables: header row shaded and bold, numbers right-aligned with thousands separators, column
  widths set, a total row bold.
- Lists in the List Bullet / List Number styles; one accent colour; black body text.
- Every figure and date exactly as in the sources; add nothing that is not in them.
- Check with `read_docx` and `review_work`; if it looks crowded or plain, fix and rerun.
