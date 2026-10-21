# Editing a .docx in the app: what exists, what we reuse (2026-10-21)

Research before building the Docs editor (decision 0019). Web claims below are the projects' own
unless marked "measured here" or "checked on npm".

## 摘要（中文）
- 市面上的 docx 在线编辑器分三类：①直接编辑 OOXML 的重型方案（OnlyOffice、Apryse，AGPL 或商用）；
  ②ProseMirror/JSON 模型加 docx 映射（SuperDoc、eigenpal/docx-editor、Casual Docs，Tiptap 的 docx 转换）；
  ③在真实文件上做外科手术式修改（我们的做法）。
- **没有现成的开源方案可以直接用**：SuperDoc 是 AGPL（商用另购授权）；eigenpal 的核心是 Apache-2.0，
  但评论、修订和 editor-api 属于 Pro（商用协议）；Tiptap 的 docx 导入导出是付费云服务；OnlyOffice 是 AGPL。
- **我们的方案有依据**：这些项目里做得最好的几个，做法都是「未建模的内容原样保留」「用 round-trip 审计测试守住保真」。
  我在本地实测：用 python-docx 改一个段落再保存，其余 8 个段落逐字节相同，评论和修订都在，除 document.xml 外的所有部分不变。
- **前端用 Tiptap 3**（MIT；React 19 可用；标题、列表、引用、分隔线、下划线、链接、表格、图片、斜线菜单、浮条全是 MIT 扩展），
  schema 限定为我们的子集；docx 的读写自己写，不用任何「编辑器到 docx」的转换器。

## Landscape
| Project | Approach | License | Fits us? |
|---|---|---|---|
| [SuperDoc](https://github.com/superdoc-dev/superdoc) | Own OOXML-backed model, browser and headless Node SDK; V2 moved off ProseMirror | AGPL-3.0, commercial licence for proprietary use; 1.1k stars | No: copyleft, and its model replaces ours |
| [eigenpal/docx-editor](https://github.com/eigenpal/docx-editor) | WYSIWYG React/Vue editor, headless layout engine; "preserves unsupported OOXML" | Apache-2.0, but the review module (comments, tracked changes), editor-api and PDF are Pro | Partly: useful as a fidelity reference, not as a dependency |
| [Casual Docs](https://github.com/CasualOffice/docs) | Fork of eigenpal's MIT version; ProseMirror, native parser and serializer; round-trip audit script diffing `document.xml`; 61 stars | Apache-2.0 / MIT | Reference for the audit method only |
| Tiptap docx conversion | Cloud service, import and export | Pro, paid; legacy import lacks page breaks, headers, rules, text styles ([docs](https://tiptap.dev/docs/guides/legacy-conversion)) | No |
| OnlyOffice Docs | Native OOXML editing | AGPL-3.0; proprietary products need a commercial licence ([FAQ](https://helpcenter.onlyoffice.com/docs/faq/docs-community.aspx)) | No (and a server) |
| Apryse | Native OOXML editing | Commercial | No |
| Pandoc | Markdown ⇄ docx; styles only from `--reference-doc`; headings, quotes, links ignore `custom-style` | GPL, a binary | Confirms 0013: styles belong to the reference document |

## What the good ones agree on (and we adopt)
1. **Unmodeled content is preserved, not dropped.** eigenpal's [fidelity page](https://www.docx-editor.dev/docs/1.x/word-fidelity)
   has a round-trip column ("Preserved": charts, ink, page background, hidden text kept as inert markup on save).
   A [proposal in Serenity](https://github.com/BarMal/Serenity/issues/1896) calls these opaque nodes anchored to their
   paragraph. Our locked blocks are the same idea.
2. **A round-trip audit guards fidelity**: parse, write, diff `document.xml` (Casual Docs); fixtures from real documents
   ([UseJunior](https://www.usejunior.ai/engineering/round-trip-fidelity-and-tracked-changes-vs-python-docx):
   "edit surgically, change only what you need", failures were drifting numbering, vanished comments, odd redlines).
3. **Optimistic revision on every write**: SuperDoc's mutations take an `expectedRevision`
   ([engine write-up](https://www.superdoc.dev/changelog/2026-03-22-document-engine)). That is our file-version guard.
4. **The model picks an operation, not XML**: the same write-up says LLM-written OOXML differs on every run.
5. **OOXML traps** ([how to write real tracked changes](https://www.vaquill.ai/engineering/word-tracked-changes-in-python)):
   deleted text needs `w:delText`, `w:id` unique across the document, build tags with `qn()`, a comment needs start, end and
   reference sharing one id, retag runs instead of rebuilding them (keeps `xml:space`). Test accept and reject in real Word.

## Measured here
python-docx opened a document written by our tools (a comment, an insertion and a deletion, a table), one paragraph was
changed by replacing its runs, and it was saved: every part but `word/document.xml` is byte-identical, `comments.xml` is
unchanged, the `w:ins`, `w:del` and `commentRangeStart` markers are still there, and of 9 paragraphs only the edited one
differs (c14n). So the surgical writer of 0019 is sound for what python-docx models; run-level formatting of an edited
paragraph is rebuilt, which 0019 accepts.

## The editor library
Checked on npm today: Tiptap 3.32.0 and prosemirror-view 1.42.6 are MIT; `@tiptap/react` accepts React 17–19 (we use 19);
starter-kit holds heading, blockquote, lists, horizontal rule, underline and link; `extension-table`, `extension-image`,
`extension-placeholder`, `suggestion` (slash menu) and `extension-bubble-menu` are MIT as well. Alternatives: Lexical (MIT,
tables and menus are more to build), BlockNote (MPL-2.0, a Notion-style block editor, a worse fit for flowing text).
Costs to watch: bundle size (the build already warns about chunks over 500 kB), IME composition, table editing.

## Recommendation
- Backend: our own python-docx and lxml block reader and writer (0019), with a round-trip audit test over real documents,
  locked blocks for what it does not model, and one document-wide counter for any revision ids it ever writes.
- Frontend: Tiptap 3 with a schema limited to the 0019 set; the Word-layout view stays docx-preview (0014).
- Do not adopt SuperDoc, eigenpal, Tiptap's converter or OnlyOffice.
- Not yet checked: coscribe's own licence (only matters if AGPL code were ever wanted), real Word behaviour for the writer,
  Tiptap's behaviour with Chinese IME in the packaged Electron app.
