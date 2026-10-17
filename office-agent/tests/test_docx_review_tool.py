import zipfile
from pathlib import Path

import pytest
from docx import Document
from lxml import etree

from coscribe.tools.office.document_tools import build_document_tools

W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"

CONTRACT = """\
# Service agreement

## Price

The total price is 100 dollars, due within 30 days of the invoice date. {{comment: Final price?}}

## Term

The agreement runs for one year.
"""


def _tools(root: Path) -> dict[str, object]:
    return {tool.__name__: tool for tool in build_document_tools(root)}  # type: ignore[attr-defined]


@pytest.fixture
def redline(tmp_path: Path) -> dict[str, object]:
    tools = _tools(tmp_path)
    tools["write_docx"](path="c.docx", content=CONTRACT, comment_author="Ana Lee")
    tools["insert_docx_text"](path="c.docx", text=" (extended)", context_before="30 days")
    tools["delete_docx_text"](path="c.docx", text="100 dollars")
    return tools


def _body(tmp_path: Path) -> str:
    return "\n".join(p.text for p in Document(tmp_path / "c.docx").paragraphs)


def test_read_lists_changes_under_their_heading_and_the_comment_with_its_words(
    tmp_path: Path, redline: dict
) -> None:
    review = redline["read_docx_review"](path="c.docx")

    kinds = {(c["kind"], c["text"], c["under"]) for c in review["changes"]}
    assert kinds == {("insert", " (extended)", "Price"), ("delete", "100 dollars", "Price")}
    assert len({c["id"] for c in review["changes"]}) == 2
    [comment] = review["comments"]
    assert comment["author"] == "Ana Lee"
    assert comment["text"] == "Final price?"
    assert "invoice date" in comment["anchor"]
    assert comment["done"] is False and comment["replies"] == []


def test_one_change_is_accepted_and_the_other_left_for_review(
    tmp_path: Path, redline: dict
) -> None:
    changes = redline["read_docx_review"](path="c.docx")["changes"]
    insert = next(c for c in changes if c["kind"] == "insert")

    result = redline["edit_docx_review"](
        path="c.docx", operations=[{"op": "accept", "change": insert["id"]}]
    )

    assert result["changes_left"] == 1
    left = redline["read_docx_review"](path="c.docx")["changes"]
    assert [c["kind"] for c in left] == ["delete"]
    redline["edit_docx_review"](path="c.docx", operations=[{"op": "reject_all"}])
    assert "The total price is 100 dollars, due within 30 days (extended) of" in _body(tmp_path)


def test_a_reply_threads_under_its_comment_and_resolving_closes_the_thread(
    tmp_path: Path, redline: dict
) -> None:
    [comment] = redline["read_docx_review"](path="c.docx")["comments"]

    redline["edit_docx_review"](
        path="c.docx",
        operations=[
            {"op": "reply", "comment": comment["id"], "text": "Yes, agreed with finance."},
            {"op": "resolve", "comment": comment["id"]},
        ],
        author="Ben Ode",
    )

    [thread] = redline["read_docx_review"](path="c.docx")["comments"]
    assert thread["done"] is True
    [reply] = thread["replies"]
    assert (reply["author"], reply["text"], reply["initials"]) == (
        "Ben Ode",
        "Yes, agreed with finance.",
        "BO",
    )
    assert reply["done"] is True
    with zipfile.ZipFile(tmp_path / "c.docx") as z:
        document = z.read("word/document.xml").decode()
        assert "word/commentsExtended.xml" in z.namelist()
        assert "commentsExtended+xml" in z.read("[Content_Types].xml").decode()
    # Word draws a reply only where the document carries its anchor and reference.
    assert document.count(f'w:commentReference w:id="{reply["id"]}"') == 1
    assert document.count(f'w:commentRangeStart w:id="{reply["id"]}"') == 1

    redline["edit_docx_review"](
        path="c.docx", operations=[{"op": "reopen", "comment": reply["id"]}]
    )
    assert redline["read_docx_review"](path="c.docx")["comments"][0]["done"] is False


def test_a_new_comment_anchors_to_just_the_words_given(tmp_path: Path, redline: dict) -> None:
    result = redline["edit_docx_review"](
        path="c.docx", operations=[{"op": "comment", "on": "one year", "text": "Two?"}]
    )

    assert result["open_comments"] == 2
    new = redline["read_docx_review"](path="c.docx")["comments"][-1]
    assert (new["anchor"], new["text"], new["author"]) == ("one year", "Two?", "Coscribe")
    assert "The agreement runs for one year." in _body(tmp_path)


def test_a_failing_operation_saves_nothing(tmp_path: Path, redline: dict) -> None:
    before = (tmp_path / "c.docx").read_bytes()

    with pytest.raises(ValueError, match="operation 2: .*appear 0 times"):
        redline["edit_docx_review"](
            path="c.docx",
            operations=[
                {"op": "accept_all"},
                {"op": "comment", "on": "no such words", "text": "x"},
            ],
        )
    with pytest.raises(ValueError, match="no tracked change with id 999"):
        redline["edit_docx_review"](path="c.docx", operations=[{"op": "reject", "change": "999"}])

    assert (tmp_path / "c.docx").read_bytes() == before


def test_threads_written_by_word_are_read_from_comments_extended(
    tmp_path: Path, redline: dict
) -> None:
    [comment] = redline["read_docx_review"](path="c.docx")["comments"]
    redline["edit_docx_review"](
        path="c.docx", operations=[{"op": "reply", "comment": comment["id"], "text": "Noted."}]
    )
    # As Word leaves it: done on the thread's first comment, under its own part name.
    with zipfile.ZipFile(tmp_path / "c.docx") as z:
        parts = {n: z.read(n) for n in z.namelist()}
    extended = etree.fromstring(parts["word/commentsExtended.xml"])
    first = next(ex for ex in extended if not ex.get(f"{W15}paraIdParent"))
    first.set(f"{W15}done", "1")
    parts["word/commentsExtended.xml"] = etree.tostring(extended)
    with zipfile.ZipFile(tmp_path / "c.docx", "w") as z:
        for name, blob in parts.items():
            z.writestr(name, blob)

    [thread] = redline["read_docx_review"](path="c.docx")["comments"]
    assert thread["done"] is True
    assert [r["text"] for r in thread["replies"]] == ["Noted."]
