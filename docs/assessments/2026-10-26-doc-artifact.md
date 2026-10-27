# Design note: the Doc artifact, a markdown document people and coscribe edit together (2026-10-26)

Design before code: it adds a kind of artifact and changes where a written document lives. Status:
**accepted** (2026-10-26, #646 merged by the maintainer). It follows from `2026-10-26-word-spec-gate.md` (the spec
route for Word did not beat markdown) and from the maintainer's view that drawing any .docx
faithfully is not a direction worth more work. It rests on 0001 (a fixed, cached tool list), 0012 (no
LibreOffice), 0015 (comments live beside the file, not in it), 0019 (the .docx is the artifact: it
stays true for Word files) and 0020. It does not touch Word documents or the `write_docx` route.

## 中文摘要

1. **要加什么**：Artifacts 里的 Doc——正本是一个 markdown 文件，内容和结构是主角，样式很少。我（coscribe）
   用普通的文件工具按块精确改它；人像改文章一样在编辑器里改、给 coscribe 留言（和 PPT 同一套评论）；
   可以导出 Markdown、PDF、Word。
2. **不做什么**：不画任意 .docx。Word 文件路线（`write_docx` 写 markdown、编辑工具）不变，现有 Word 面板
   冻结：只修错，不加功能。
3. **正本格式**：markdown（GFM：表格、任务列表、图片）加两个小扩展，都是 AI 本来就会写的写法：提示框用
   `> [!NOTE]`，图表用 ```` ```chart ```` 围栏里放一个管道表。头部 front matter 里写 `coscribe: doc` 作标记。
   不再发明 `:::` 之类的语法（那次评测里，4 个该用的新文档任务模型没用上，用上的短文档又加了不必要的封面）。
4. **导出**：Markdown 去掉 front matter；PDF 走浏览器打印对话框（Design 页面已经这样做）；Word 走现有的
   `write_docx` 加 `add_docx_chart` 和 `add_docx_image`。
5. **下一步**：接受后分六个 PR 做（第 5 节），第一个只做解析和"按块改"。

## 1. Why

- Drawing an arbitrary .docx is open-ended: every shape nobody taught the canvas shows wrong, and the
  work on the look layer (styles, page sheet, charts) only narrowed it. The maintainer's view, which
  this note follows: do not add native .docx preview; keep the Word route as it is.
- An HTML artifact is a page: any layout, any interaction, but the content is code, so it is not
  something several people edit like an article. A Doc is the opposite: content and structure first,
  few styles, edited by hand and by coscribe, exported when it must be a file.
- Claude's online Docs, as the maintainer described them, make the same trade: the structure is the
  document, and Word, PDF and markdown are exports. (Not checked against Claude's own documentation.)

## 2. The Doc

**Source.** One markdown file, `name.md`, whose first lines are a front matter with `coscribe: doc` (and
a `title`). A markdown file without the marker is not an artifact. Beside it, a folder `name.doc/`
holds what must not be in the text: `comments.json`, `assets/` (pictures the person adds) and the kept
versions. This is how a deck keeps its pages folder (0010, 0015).

**Content.** Commonmark and GFM: headings, paragraphs with bold, italic, code and links, lists, task
lists, tables, quotes, code blocks, pictures by relative path. Two additions, both written the way a
model already writes them:

- a call-out is a quote opened with `[!NOTE]`, `[!TIP]`, `[!WARNING]` or `[!IMPORTANT]` (GitHub's alerts);
- a chart is a fenced block, `chart`, with a first line `bar`, `line` or `pie` (and an optional
  title) and then a pipe table; it is drawn from the table, so text, table and chart can be kept to
  the same figures by the writer.

There is no colour, font or size in the source. A Doc has one house look in the editor and in the
exports.

**Editing by coscribe.** With the ordinary file tools (`read_file`, `edit_file`, `write_file`): a
model is good at exact text edits in markdown, and there is no new write tool. What is new: a skill
that says when a Doc is the right output and what the marker and the two additions are, and the
comment tools (below).

**Editing by a person.** The editor is the one built for Word documents (Tiptap: toolbar, bubble menu,
slash menu, undo), working on markdown blocks. The markdown is parsed into blocks with their line
ranges (markdown-it-py gives each block's range); an edited block is written back as its own text and
every other line is left byte for byte, so a person's edit never reformats what coscribe wrote
and coscribe's next edit applies to text that is still there. This is 0019's rule ("save only the
changed blocks") carried over. Serializing one block back needs a serializer for the node set above;
the first PR checks whether Tiptap's own markdown extension does it and writes the small one if not.

**At the same time.** As for decks and Word files: a write that arrives after the person saved since
coscribe last read is refused with a re-read; the versions are kept so a change made behind the
person can be undone; coscribe is told once what the person changed at its next turn.

**Comments for coscribe.** The same flow as a deck's (0015, `view_comments.py`), which has no comment
tools for the model: the person adds a comment on a block, and when it is for coscribe the editor also
sends it as a chat message that quotes the block; when the turn ends the editor writes coscribe's
answer back as a reply to that comment. `comments.json` in the side folder holds each comment with
its replies, resolved state and an anchor: the text of its block and which copy of that text it is,
so it follows its block when blocks are added or removed and is kept, shown as detached, when the
text is gone. (An earlier version of this note had four deferred tools and a next-turn note; the
deck does neither, and no new tool keeps the tool list fixed, 0001.)

**The card.** An artifact card like a deck's: title, a "Doc" badge, last change, and a thumbnail the
frontend draws from the first blocks. Same menu (rename, delete to the recycle bin, duplicate,
pin, copy path), a "New Doc" tile beside the others.

## 3. Export

| To | How |
|---|---|
| Markdown | the file without its front matter; pictures as files in a folder, or inline when there are few |
| PDF | the rendered Doc in a sandboxed frame and the browser's print dialog, as the Design artifact does; no new dependency, no LibreOffice (0012). A direct file from the desktop app (Electron's `printToPDF`) is a later nicety, not part of this design |
| Word | `write_docx` on the markdown, then `add_docx_chart` and `add_docx_image` for the chart blocks and pictures: the route that exists, with its house style |

Word is the one export that is not exact: callouts become shaded paragraphs, and a Word user edits
the copy, not the Doc. The export menu says so in one line.

## 4. The Word panel

Frozen: it keeps opening .docx files, with the look layer, comments, versions and the AI sync it has.
No new feature goes into it and no effort goes into drawing more of a .docx; a bug in what it does
today is still fixed. It is not removed in this note: whether to remove it is decided once the Doc has
been in use. coscribe's rule for which to write: a Doc when the person asks for a document, report,
article or notes to keep in the app; a .docx only when they ask for a Word file, give a template or a
file to edit.

## 5. Steps

1. The format: front matter marker, block parsing with line ranges, the replace-one-block function,
   the chart and call-out blocks, tests (about 400 lines, `tools`, adds `markdown-it-py` as a
   dependency).
2. Routes and versions: read blocks, save changed blocks, the refused-after-save rule, kept
   versions, the note of what the person changed (about 400).
3. Comments: `comments.json` with anchored comments, replies, resolve and delete, and their routes
   (about 400; mirrors the deck; the message to coscribe and the reply are the editor's, step 4).
4. The editor: markdown blocks in the existing Tiptap panel, the Doc look, comments in the margin
   (about 600, frontend; the Word panel's code is reused, not changed).
5. Artifacts: the card, the listing kind, the New Doc tile, the Export menu (about 400).
6. The skill and a measurement: when a Doc is chosen, and the evaluation's document tasks written
   as Docs and judged on the rendered Doc (about 300 and a run).

## 6. Not decided, and risks

- Real-time editing by several people at once is not designed here: "people and coscribe", with
  comments, is. If it is wanted later it needs a sync layer this format does not prevent.
- The tables a model writes in markdown have no column widths or merged cells: a Doc with a wide
  table is scrolled in the editor, and wide tables in the Word export use the house style's fit.
- A chart block is the one extension a model must learn; the skill carries one example and the
  editor shows a bad block as the code it is, not an error.
- Pictures: where a picture from the web or the model's own image goes (`name.doc/assets/`) and
  how big it may be are settled in step 2.
- A long Doc is one file: a limit on size and a "split" suggestion are not designed here.
- Not measured: whether models choose a Doc and write the two additions without being told in the
  prompt; step 6 measures it before the skill is made the default.
