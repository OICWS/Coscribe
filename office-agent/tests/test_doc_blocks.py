"""A Doc (decision 0025): a markdown file read as blocks, and changed one block at a time so that
every other line stays as it was written."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from coscribe.tools.office.doc import (
    BlocksRefused,
    Delete,
    Insert,
    NotADoc,
    Replace,
    apply_edits,
    is_doc,
    parse_chart,
    read_doc,
)

HEAD = "---\ncoscribe: doc\ntitle: Notes\n---\n\n"
BODY = """\
# Plan

First paragraph,
over two lines.

- one
- two

| a | b |
| - | - |
| 1 | 2 |

> [!NOTE]
> Mind the date.

> a plain quote

```chart
bar Sales
| q | s |
| --- | --- |
| Q1 | 3 |
| Q2 | 5 |
```

```python
print("hi")
```

---

[ref]: https://example.com
"""
DOC = HEAD + BODY


def _kinds(source: str) -> list[str]:
    return [b.kind for b in read_doc(source).blocks]


def test_a_file_is_a_doc_only_with_the_marker() -> None:
    assert is_doc(DOC)
    assert not is_doc(BODY)
    assert not is_doc("---\ntitle: x\n---\n\ntext\n")
    with pytest.raises(NotADoc):
        read_doc(BODY)


def test_each_block_has_its_kind_and_the_lines_it_covers() -> None:
    assert _kinds(DOC) == [
        "heading",
        "paragraph",
        "list",
        "table",
        "callout",
        "quote",
        "chart",
        "code",
        "rule",
        "other",
    ]
    doc = read_doc(DOC)
    paragraph = doc.blocks[1]
    assert paragraph.text == "First paragraph,\nover two lines."
    lines = DOC.splitlines()
    assert "\n".join(lines[paragraph.start : paragraph.end]) == paragraph.text
    assert doc.meta["title"] == "Notes"


def test_a_link_reference_definition_is_a_block_so_no_line_is_outside_one() -> None:
    doc = read_doc(DOC)
    lines = DOC.splitlines(keepends=True)
    covered = {n for b in doc.blocks for n in range(b.start, b.end)}
    assert all(n in covered for n, line in enumerate(lines) if line.strip() and n >= doc.body_start)


def test_the_front_matter_is_not_a_block() -> None:
    assert read_doc(DOC).blocks[0].text == "# Plan"
    assert read_doc(DOC).body_start == 4


@pytest.mark.parametrize("kind", ["NOTE", "tip", "Important", "WARNING", "CAUTION"])
def test_call_outs_are_github_alerts(kind: str) -> None:
    assert _kinds(HEAD + f"> [!{kind}]\n> text\n") == ["callout"]


def test_replacing_a_block_leaves_every_other_line_as_it_was() -> None:
    doc = read_doc(DOC)
    paragraph = doc.blocks[1]

    out = apply_edits(DOC, [Replace(1, paragraph.text, "New text.")])

    assert out == DOC.replace(paragraph.text, "New text.")


def test_a_block_that_changed_since_it_was_read_is_refused_and_nothing_is_written() -> None:
    with pytest.raises(BlocksRefused, match="Block 1 changed"):
        apply_edits(DOC, [Replace(1, "something else", "New text.")])
    with pytest.raises(BlocksRefused, match="Block 0 changed"):
        apply_edits(DOC, [Delete(0, "# Another title")])


def test_insert_after_a_block_and_before_the_first() -> None:
    out = apply_edits(DOC, [Insert(0, "Intro."), Insert(-1, "Top.")])

    assert _kinds(out)[:4] == ["paragraph", "heading", "paragraph", "paragraph"]
    assert read_doc(out).blocks[0].text == "Top."
    assert read_doc(out).blocks[2].text == "Intro."
    assert out.endswith(DOC[-60:])


def test_delete_removes_the_block_and_one_blank_run() -> None:
    doc = read_doc(DOC)
    out = apply_edits(DOC, [Delete(2, doc.blocks[2].text)])

    assert "- one" not in out
    assert out == DOC.replace("- one\n- two\n\n", "")


def test_deleting_the_last_block_removes_the_blank_line_before_it() -> None:
    source = HEAD + "# A\n\nlast\n"
    out = apply_edits(source, [Delete(1, "last")])

    assert out == HEAD + "# A\n"


def test_two_edits_to_one_block_or_an_insert_after_a_deleted_block_are_refused() -> None:
    with pytest.raises(BlocksRefused, match="twice"):
        apply_edits(DOC, [Replace(1, read_doc(DOC).blocks[1].text, "x"), Delete(1, "y")])
    with pytest.raises(BlocksRefused, match="deleted in the same save"):
        apply_edits(DOC, [Delete(0, "# Plan"), Insert(0, "x")])
    with pytest.raises(BlocksRefused, match="no block 99"):
        apply_edits(DOC, [Insert(99, "x")])


def test_several_edits_in_one_save_apply_against_the_read_they_name() -> None:
    doc = read_doc(DOC)
    out = apply_edits(
        DOC,
        [
            Replace(0, "# Plan", "# Plan v2"),
            Replace(2, doc.blocks[2].text, "- only"),
            Insert(2, "Between."),
        ],
    )
    new = read_doc(out)
    assert new.blocks[0].text == "# Plan v2"
    assert [b.text for b in new.blocks[2:4]] == ["- only", "Between."]


def test_a_file_with_crlf_keeps_its_line_endings() -> None:
    source = DOC.replace("\n", "\r\n")
    out = apply_edits(source, [Replace(1, read_doc(source).blocks[1].text, "Two\nlines.")])

    assert "Two\r\nlines." in out
    assert "\n" not in out.replace("\r\n", "")


def test_a_last_block_without_a_final_newline_stays_without_one() -> None:
    source = HEAD + "# A\n\nend"
    assert apply_edits(source, [Replace(1, "end", "new end")]) == HEAD + "# A\n\nnew end"
    assert apply_edits(source, [Insert(1, "after")]).endswith("end\n\nafter\n")


def test_adjacent_blocks_without_a_blank_line_stay_apart_when_one_is_inserted_between() -> None:
    source = HEAD + "# A\ntext\n"
    out = apply_edits(source, [Insert(0, "mid")])

    assert [b.text for b in read_doc(out).blocks] == ["# A", "mid", "text"]


def test_insert_into_a_doc_with_no_blocks() -> None:
    assert read_doc(HEAD).blocks == []
    assert read_doc(apply_edits(HEAD, [Insert(-1, "# First")])).blocks[0].text == "# First"


_PARTS = [b.text for b in read_doc(DOC).blocks]


@given(st.integers(0, len(_PARTS) - 1), st.text(alphabet="abc xyz", min_size=1, max_size=20))
def test_a_replace_changes_only_its_own_lines(index: int, text: str) -> None:
    text = text.strip() or "x"
    doc = read_doc(DOC)
    block = doc.blocks[index]
    if block.kind == "other":
        return
    out = apply_edits(DOC, [Replace(index, block.text, f"para {text}")])

    before = DOC.splitlines(keepends=True)
    after = out.splitlines(keepends=True)
    assert before[: block.start] == after[: block.start]
    assert before[block.end :] == after[len(after) - (len(before) - block.end) :]


@given(st.integers(0, len(_PARTS) - 1))
def test_replacing_a_block_with_itself_changes_nothing(index: int) -> None:
    block = read_doc(DOC).blocks[index]

    assert apply_edits(DOC, [Replace(index, block.text, block.text)]) == DOC


def test_a_chart_block_is_read_from_its_table() -> None:
    chart = parse_chart(read_doc(DOC).blocks[6].text)

    assert (chart.kind, chart.title) == ("bar", "Sales")
    assert chart.categories == ["Q1", "Q2"]
    assert chart.series == {"s": [3.0, 5.0]}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("```chart\nbar\n```", "header row"),
        ("```chart\nradar X\n| a | b |\n| --- | --- |\n| x | 1 |\n```", "first line names one"),
        (
            "```chart\npie T\n| a | b | c |\n| --- | --- | --- |\n| x | 1 | 2 |\n```",
            "one data column",
        ),
        ("no fence", "opens with"),
    ],
)
def test_a_bad_chart_says_what_to_change(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_chart(text)
