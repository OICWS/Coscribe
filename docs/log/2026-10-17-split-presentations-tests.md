# `test_presentations_tool.py` split by concern (shipped)

Why: #348 item 5. The file was 6,864 lines, the largest test file, and a change to one PowerPoint tool meant finding its tests inside it.

## Shipped
- `tests/tools/office/pptx/` holds 24 files by concern (write and read, QA checks, layouts, charts, images, shape effects, notes, transitions, animation, audio, hyperlinks, delivery check, theme colors, theme, templates, text and shape editing, tables, icons, slide structure, formula). The largest is 699 lines. Builders used by several files are in `helpers.py`.
- Test bodies are unchanged and the count is the same: 367 tests before and after, and the sorted list of test names is identical. Only two paths changed: `Path(__file__).parent.parent` became `parents[4]` in the two template tests, because the file is deeper. Imports of the shared builders and of `tests.libreoffice_probe` were rewritten.
- The pptx card's Tests line points to the new directory.

## Not verified
- The LibreOffice-marked tests depend on a working `soffice`; in this container one of them fails or passes depending on parallel runs, before and after the move alike. They run on the CI runner.

## Follow-ups
- `web/test_chat.py` and `web/test_threads.py` by route group.
