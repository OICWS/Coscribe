---
name: Docs
description: Write a document, report, proposal, plan, guide, letter, resume or manual as a Doc, the app's own editable document (a Markdown file); the default for writing the person wants to keep, edit, comment on or send, unless they ask for Word, a .docx, a template, or tracked changes. Load before writing one.
---
A Doc is a Markdown file that the person edits in the app (like a Google Doc) and that you edit
with the ordinary file tools. It exports to Word, PDF and Markdown from its menu, so a request
for "a file to send, print or submit" is not a reason to write .docx.

## When

- A Doc: documents, reports, proposals, plans, specs, guides, letters, resumes, manuals, notes
  to keep. The person did not name a format, or named only what they will do with it.
- Chat, no file: a question, or a short comparison or summary.
- A Word file (`write_docx`, "Word Documents" skill): the person says Word or .docx, gives a
  .docx to change or use as a template, or wants tracked changes.

## The file

Write one `.md` file with `write_file`, named for what it is (`launch-plan.md`). It starts with:

    ---
    coscribe: doc
    ---

without that marker the app treats it as plain Markdown, not a Doc. Then the body, one block
after another with a blank line between blocks:

- `#` once for the title, `##` and `###` for sections; no deeper.
- Paragraphs; `-` bullets; `1.` numbered items; `- [ ]` and `- [x]` checklists (a list holds
  one kind of item).
- A table is pipe rows with a `---` separator row: put figures a reader compares in one.
- Bold, italic, `code` and links. No HTML.
- A callout is a quote that starts with its kind, one of NOTE, TIP, IMPORTANT, WARNING,
  CAUTION; its body is plain paragraphs:

      > [!WARNING]
      > Budget is not final.

- A chart is a fenced block named `chart`: its first line is `bar`, `line` or `pie` and a
  title; then a pipe table (a category column, then one numeric column per series; a pie has
  one):

      ```chart
      bar Sales by quarter
      | Quarter | Sales |
      | --- | --- |
      | Q1 | 120 |
      | Q2 | 150 |
      ```

- A picture is `![what it shows](name.doc/assets/chart.png)`: copy the image into the folder
  `<file name without .md>.doc/assets/` first (`copy_file`; PNG, JPEG, GIF or WebP).

Decide who reads it and what they must see first: the opening says what the document is and its
point in two lines. Every figure, date and name exactly as in the sources; add nothing they do
not contain. Say the file's name when it is done.

## Changing a Doc

The person may be editing it too. Read the file again before you change it, and change only
what was asked, with `edit_file` (a Doc is not rewritten whole): the app keeps what you did not
touch, and tells you at your next turn which blocks the person changed meanwhile. Keep the
front matter and the blank lines between blocks as they are.

## Comments

A message that starts `Comment on <file>` is a comment the person made on the words it quotes
(`On "…":`), or several numbered ones. Answer in chat, briefly, to each: the app writes your
answer under the comment. Change the Doc only when a comment asks for a change, and then say
what you changed.
