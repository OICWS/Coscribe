"""The Word skill of each route the Word evaluation compares. `current` is the built-in skill as it
is; `spec` adds the spec grammar of decision 0024; `script` is the route of
`docs/assessments/2026-10-16-word-quality.md` (a python-docx script writes the document whole).
The three differ only in the "A new document" part, so a difference in the results is that part's.

    python -m evals.docx.routes --out evals/runs/routes
    python -m evals.run --kind docx --word-skill evals/runs/routes/spec.md --out evals/runs/spec
"""

from __future__ import annotations

import argparse
from pathlib import Path

BUILTIN = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "coscribe"
    / "builtin_skills"
    / "word"
    / "SKILL.md"
)
_START = "## A new document"
_END = "## Changing an existing document's structure"
_PICTURES = (
    "`write_docx` has no syntax for them. Write the document first, then call\n`add_docx_chart("
)

SPEC_SECTION = """\
## A designed document: the spec

For a new report, proposal or summary that should look designed, give `write_docx` a spec: a YAML
head, then markdown with a few components. The spec says what the document holds, never how it
looks: there are no colours, fonts or sizes in it, the theme sets them, so never write any.

The head, all optional: `title`, `subtitle`, `author`, `date`, `cover` (`band`, `rule` or `none`),
`toc` (true), `header`, `footer`, `facts`, `design_system` (the name of one in the person's
library; leave it out for the house style). The head ends with a line `---`, like the one that
opens it.

Components are a fence `:::name args` closed by `:::`:

- `:::stats`: two to four lines `label | value | change` (change is optional): the headline
  figures, shown as cards.
- `:::callout info|success|warn|danger`: a short paragraph the reader must not miss, such as a
  risk or a decision.
- `:::chart bar|line|pie Title`: a pipe table of the data (a category column, then one numeric
  column per series; a pie takes one), and an optional `caption: ...` line. It is a native Word
  chart. Write the numbers in the chart table without thousands separators.
- `:::figure path`: a picture from the workspace; the body is its caption.
- `:::pagebreak`.

Everything else stays markdown: `#` headings (a level at a time), lists, pipe tables.

A figure that appears more than once is defined once in the head and written as `{fact:name}`:

    facts:
      revenue: 12.8 M

so the text, the table and the chart cannot disagree.

Plan before you write a report of several sections: list its sections, who reads it, the figures
that must appear and which component shows each, then write the spec. After `write_docx`, read
`check` in its result: each item names a place and the change that clears it. Fix them all in one
more `write_docx` call (`overwrite=True`).

A spec is for a new document. Editing a user's file stays with `edit_docx_structure` and the
replace tools; a document on a `template_path` or with `track_changes` takes plain markdown.

"""

SCRIPT_SECTION = """\
## A new document

Write a new document whole in one `run_python_script` with python-docx, then check it with
`read_docx` and `review_work`; if it looks crowded or plain, fix it and run the script again.

- Styles before text: the Normal font and size once (for Chinese also the East Asian font), line
  and paragraph spacing; Title, Heading 1 and Heading 2 defined and used for every heading.
- Page: A4 unless the reader is American; margins; a footer with the page number; a header with
  the short title where it helps.
- A first page that says what it is: title, for whom, date, the point in two lines.
- Tables: header row shaded and bold, numbers right-aligned with thousands separators, column
  widths set, a total row bold.
- Lists in the List Bullet / List Number styles; one accent colour; black body text.
- Charts: a native chart with `add_docx_chart` after the script, or a picture.
- Every figure and date exactly as in the sources; add nothing that is not in them.

"""


def _split(text: str) -> tuple[str, str, str]:
    head, _, rest = text.partition(_START)
    _, _, tail = rest.partition(_END)
    return head, _START, _END + tail


def build_routes(builtin: str) -> dict[str, str]:
    head, _, tail = _split(builtin)
    spec_text = builtin.replace(_END, SPEC_SECTION + _END, 1)
    chart_note = (
        "Inside a spec a chart is `:::chart`. To add one to a file that exists,\n"
        "call `add_docx_chart("
    )
    spec_text = spec_text.replace(_PICTURES, chart_note, 1)
    return {
        "current": builtin,
        "spec": spec_text,
        "script": head + SCRIPT_SECTION + tail,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for name, text in build_routes(BUILTIN.read_text(encoding="utf-8")).items():
        (args.out / f"{name}.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
