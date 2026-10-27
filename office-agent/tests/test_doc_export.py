"""A Doc written out for Word (decision 0025): the nearest thing the writer's subset can hold."""

from __future__ import annotations

import io

from docx import Document

from coscribe.tools import docx_from_markdown, docx_markdown

DOC = """---
coscribe: doc
---

# Launch plan

We ship *first* in **May**.

> [!WARNING]
> Budget is not final.
>
> Ask finance.

- one
- two

![the chart](plan.doc/assets/chart.png)

```chart
bar Sales
| q | n |
| --- | --- |
| Q1 | 3 |
```

<div>raw</div>

```
code line
```
"""


def test_a_doc_becomes_the_markdown_subset_word_takes() -> None:
    out = docx_markdown(DOC)

    assert out.startswith("# Launch plan\n\nWe ship *first* in **May**.")
    assert "**Warning:** Budget is not final.\n\nAsk finance." in out
    assert "- one\n- two" in out
    assert "[Picture: the chart]" in out and "plan.doc/assets" not in out
    assert "**Sales**\n\n| q | n |\n| --- | --- |\n| Q1 | 3 |" in out
    assert "<div>" not in out and "```" not in out and "code line" in out
    assert "coscribe: doc" not in out


def test_the_export_is_a_word_file_with_the_doc_in_it() -> None:
    data = docx_from_markdown(docx_markdown(DOC))

    texts = [p.text for p in Document(io.BytesIO(data)).paragraphs]
    assert "Launch plan" in texts and any("Budget is not final." in t for t in texts)
    assert len(Document(io.BytesIO(data)).tables) == 1
