"""The Word skill of each route the Word evaluation compares. `current` is the built-in skill as it
is; `script` is the route of `docs/assessments/2026-10-16-word-quality.md` (a python-docx script
writes the document whole). They differ only in the "A new document" part, so a difference in the
results is that part's.

    python -m evals.docx.routes --out evals/runs/routes
    python -m evals.run --kind docx --word-skill evals/runs/routes/script.md --out evals/runs/script
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
    return {
        "current": builtin,
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
