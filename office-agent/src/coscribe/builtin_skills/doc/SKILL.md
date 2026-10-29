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

## Writing it

- Decide who reads it and what they must see first: the opening says what the document is and
  its point in two lines.
- Every figure, date and name exactly as in the sources; add nothing they do not contain. What
  only the person knows and you were not told (a date, a name, an amount, what they did in a
  job, a skill they have) is a placeholder in brackets, `[date]`, `[a result you achieved]`,
  never a plausible guess: they will sign or send this.
- Say each fact once, where it belongs; a later section points back instead of repeating it.
- Write about the subject, never about the document: no "this note covers", "further detail can
  be added on request" or a closing summary of what was said.
- The length the brief asks for: a letter or memo fits on a page, with no `#` title (it opens
  with the date or the greeting); a plan or report has the sections its content needs, not a
  standard set.
- A chart shows figures that are also in the text or a table, in the same order.

Say the file's name when it is done, and list the placeholders the person must fill.

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
