"""The Docs skill's own examples are read by the app's parsers as the blocks it says they are."""

from __future__ import annotations

import re
import textwrap

from coscribe.tools import load_builtin_skills
from coscribe.tools.office.doc import is_doc, parse_chart, read_doc


def _skill() -> str:
    return next(s for s in load_builtin_skills() if s.name == "Docs").body


def test_the_skills_marker_makes_a_doc_and_its_callout_and_chart_are_read_as_such() -> None:
    body = _skill()
    marker = re.search(r"^    ---\n    coscribe: doc\n    ---$", body, re.M)
    callout = re.search(r"^      > \[!WARNING\]\n      > Budget is not final\.$", body, re.M)
    chart = re.search(r"^      ```chart\n(?:      .*\n)+?      ```$", body, re.M)
    assert marker and callout and chart

    doc_source = (
        textwrap.dedent(marker.group(0))
        + "\n\n# T\n\n"
        + "\n\n".join(textwrap.dedent(part.group(0)) for part in (callout, chart))
    )

    assert is_doc(doc_source)
    kinds = [b.kind for b in read_doc(doc_source).blocks]
    assert kinds == ["heading", "callout", "chart"]
    chart_block = read_doc(doc_source).blocks[2]
    parsed = parse_chart(chart_block.text)
    assert (parsed.kind, parsed.categories, parsed.series) == (
        "bar",
        ["Q1", "Q2"],
        {"Sales": [120.0, 150.0]},
    )


def test_the_skill_says_when_not_to_write_a_doc() -> None:
    body = _skill()

    assert "write_docx" in body and "tracked changes" in body and ".docx" in body
