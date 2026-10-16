# Deck and PDF previews drawn without LibreOffice (shipped)

Why: every page preview went through a LibreOffice found on the user's machine, which Windows
users do not have, so the model and the approval card saw no pictures. Decision
[0012](../decisions/0012-the-product-does-not-depend-on-libreoffice.md), step 1.

## Shipped
- `tools/_svg_preview.py`: a deck whose SVG pages built it (deck and pages unchanged since the
  build, `engine.build.built_pages`) is previewed page by page from those SVGs with resvg
  (`resvg-py` 0.5.0, MPL-2.0, a 2.9 MB wheel), about 0.15 s a page. A native chart or table is a
  labelled dashed box of its size ("Column chart: …, PowerPoint draws it from its data").
- A PDF's thumbnail and pages are drawn with PDFium directly.
- `_thumbnail.render_thumbnail`, `render_all_page_previews` and `render_single_page_preview`
  take these paths first, so `preview_pptx`, `review_work` and the approval card's slide preview
  work without an office program; any other file still goes to LibreOffice until step 2.
- The packaged server collects `resvg_py`.

## Not verified
- On Windows: the packaged build with the `resvg_py` native module, and the fonts it finds
  (the pages ask for Microsoft YaHei, which Windows has).
- Whether the reviewer reads a chart placeholder as a defect; to be watched in the next deck
  evaluation.

## Follow-ups
- Step 2 (#319): Word and Excel files, and decks edited after their build, previewed through
  Office (COM).
