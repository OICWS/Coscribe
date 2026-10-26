# The gate for Word documents written from a spec: the three-way run (2026-10-26)

Decision 0024 says the spec route becomes the default only if it passes the gate in section 4 of
`2026-10-26-word-documents-from-a-spec.md`. This is that run. **It did not pass. `write_docx` keeps
its behaviour and the Word skill is unchanged.**

## 中文摘要

1. 三条路线、14 个任务（01–11 加新增的 12–14），DeepSeek flash 低推理强度，非高峰；每份文档同一次
   请求内盲评 3 轮（设计、内容、连贯，1–5 分）。
2. **没有通过门槛**：设计平均 spec 3.68，current 3.76，script 4.06（门槛 4.2，且要在 05、06、08、10、12
   上高于 current）。spec 在 05（+0.77）、06（+0.47）、10（+0.47）、14（+1.13）上赢，在 08（−0.57）和
   12（−1.17）上输，09（−1.07）、13（−0.93）也明显输。内容 4.11 对 4.06，不低；成本 −14%，时间 −25%。
3. 确定性检查：spec 14 个全过；current 在 14 的主题上不过（它没法套设计系统）；script 在 02 页数、
   04 模板、14 主题上不过。
4. **输的原因看渲染图是真缺陷，不是评审偏差**：短文档被模型加了封面和目录，各占近乎空白的一页；
   数字卡片里的数值折行（`128,40` / `0`）；柱状图纵轴不从 0 开始；图里的字体和正文不一致；表格后的
   段落紧贴表格。前两项是技能文字没说清何时该用，后几项是编译器的缺陷，都能改。
5. **建议**：不翻转默认。先改这六处，只重跑 spec 路线的 08、09、12、13 四个任务，和已有的 current、
   script 一起重新盲评；不过再决定是否继续。script 路线分最高，但需要用户电脑装 Python 且每次要批准，
   不能做产品默认（2026-10-16 已定）。
6. 成本说明：评测的 `cost` 是美元；三路合计 0.68 美元，约 4.6 元。

## 1. What was run

- Routes: `current` (the built-in Word skill), `spec` (the same skill with the spec grammar added),
  `script` (the 2026-10-16 route: a python-docx script writes the document). They differ only in
  the "A new document" part of the skill (`evals/docx/routes.py`).
- Tasks: the eleven of 2026-10-16 and three new ones: a report with cover, contents, stats, chart
  and shaded table (12); figures that must agree across text, table and chart (13); the same kind of
  report on a design system with a Chinese brand font (14).
- Blind judging: each task's three documents in one request, random labels, three rounds, design /
  content / coherence, DeepSeek flash. Task 10's first attempt failed on a truncated render (the disk
  filled during the run); the image was re-rendered and the task judged again.
- Checks that are exact: facts, headings, tables, charts, theme, template, pages.

## 2. Results

Design, mean of three rounds (spread is about 0.2 to 0.4):

| Task | current | spec | script | spec - current |
|---|---|---|---|---|
| 01 report from notes | 3.80 | 3.87 | 4.40 | +0.07 |
| 02 memo from a PDF | 4.43 | 4.07 | 3.27 | -0.37 |
| 03 tracked contract | 3.17 | 3.08 | 3.17 | -0.08 |
| 04 letter on a template | 4.03 | 4.10 | 3.93 | +0.07 |
| 05 table-heavy | 3.37 | 4.13 | 4.47 | +0.77 |
| 06 mixed language | 3.97 | 4.43 | 3.63 | +0.47 |
| 07 restructure | 3.13 | 3.17 | 3.20 | +0.03 |
| 08 image and caption | 4.23 | 3.67 | 4.43 | -0.57 |
| 09 proposal | 3.87 | 2.80 | 4.40 | -1.07 |
| 10 half-year summary | 3.47 | 3.93 | 4.43 | +0.47 |
| 11 restructure a report | 4.27 | 4.37 | 4.43 | +0.10 |
| 12 quarterly report | 3.73 | 2.57 | 4.20 | -1.17 |
| 13 figures agree | 4.20 | 3.27 | 4.63 | -0.93 |
| 14 brand report (Chinese) | 2.93 | 4.07 | 4.23 | +1.13 |
| **mean** | **3.76** | **3.68** | **4.06** | -0.08 |

| | current | spec | script |
|---|---|---|---|
| Content (mean) | 4.06 | 4.11 | 4.27 |
| Coherence (mean) | 4.05 | 4.10 | 4.30 |
| Cost, 14 tasks (USD) | 0.220 | 0.190 | 0.272 |
| Task time, summed (s) | 1,602 | 1,195 | 1,994 |
| Exact checks failed | 14 theme | none | 02 pages, 04 template, 14 theme |

## 3. The gate

| Criterion | Result |
|---|---|
| Every existing check passes | Yes for spec |
| Design at least 4.2 on average | **No: 3.68** |
| Above current on 05, 06, 08, 10, 12 | **No: 08 and 12 are below** |
| Content no lower than current | Yes (4.11 against 4.06) |
| Cost within 15% of current | Yes (14% less) |
| The checker finds nothing in compiled documents | **Not measured**: a write's result is not kept in the run |
| No contradicting figures on 13 | Yes (every fact and chart value found, the wrong 4,950 absent) |

## 4. Why it lost, from the rendered pages

The spec route used the grammar on 08, 09, 10, 12, 13 and 14, and wrote plain markdown on the other new
documents (01, 02, 05, 06): the model decides. Where it used it, the pages show:

1. **A cover and a contents page on a short document** (09, 12, 13): each is a nearly empty page. The
   skill never says when a cover is worth it. A one-page summary does not need one.
2. **Stat cards wrap their values** (`128,40` over `0`, `41.20` over `USD`): the value is 20 pt in a card
   a quarter of the page wide. Compiler.
3. **A bar chart's axis starts at 39,000**, which makes a 8% rise look like a tripling. Compiler.
4. **The chart's text is a serif font** and the title is not the document's. Compiler.
5. **No page numbers in the contents** in the render (Word fills them on open; LibreOffice does not),
   and the contents list sits alone on a page. The skill and the compiler.
6. **A table is followed at once by its paragraph** with no space. Compiler.

The script route wins on look because it can set anything; it also lost two exact checks and cannot
run for a person without Python, which is why it was never the product's route (2026-10-16).

## 5. Recommendation

Do not flip the default. Fix the six items above (about 150 lines and a paragraph of skill text), run
the spec route again on 08, 09, 12 and 13 only, and judge those four with the existing `current` and
`script` documents in the same requests. Cost: about 0.05 USD. If design is not then at least
current on those four and 4.2 over the fourteen, the spec stays opt-in and the compiler's fixes
still stand: they improve every document a spec writes.

Not measured: the same documents opened in Word on Windows; a repair pass after a checker finding.
