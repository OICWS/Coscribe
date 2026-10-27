"""Comments on a Doc (decision 0025): kept beside it, anchored to the text of their block."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coscribe.tools.office.doc import (
    DocCommentNotFound,
    NotADoc,
    add_doc_comment,
    apply_edits,
    delete_doc_comment,
    read_doc_comments,
    reply_to_doc_comment,
    resolve_doc_comment,
)
from coscribe.tools.office.doc.blocks import Delete, Insert, Replace

SOURCE = "---\ncoscribe: doc\n---\n\n# Plan\n\nFirst paragraph.\n\nSecond paragraph.\n"


def _doc(tmp_path: Path, text: str = SOURCE) -> Path:
    path = tmp_path / "plan.md"
    path.write_text(text, encoding="utf-8")
    return path


def _edit(path: Path, *edits: object) -> None:
    path.write_text(apply_edits(path.read_text(encoding="utf-8"), list(edits)), encoding="utf-8")  # type: ignore[arg-type]


def test_a_comment_is_kept_in_the_side_folder_and_read_back_with_its_block(tmp_path: Path) -> None:
    path = _doc(tmp_path)

    made = add_doc_comment(path, block=1, text="  Is this right?  ", author="Ana", sent=True)
    read = read_doc_comments(path)

    assert (tmp_path / "plan.doc" / "comments.json").is_file()
    assert len(read) == 1 and read[0]["id"] == made["id"]
    assert read[0]["text"] == "Is this right?"
    assert (read[0]["block"], read[0]["detached"]) == (1, False)
    assert read[0]["anchor"]["text"] == "First paragraph."
    assert (read[0]["sent"], read[0]["resolved"], read[0]["replies"]) == (True, False, [])


def test_a_comment_follows_its_block_when_blocks_are_added_or_removed_before_it(
    tmp_path: Path,
) -> None:
    path = _doc(tmp_path)
    add_doc_comment(path, block=2, text="Check this", author="Ana", sent=False)

    _edit(path, Insert(-1, "A new first block."), Insert(0, "And one more."))
    moved = read_doc_comments(path)[0]
    assert moved["block"] == 4 and moved["detached"] is False

    _edit(path, Delete(0, "A new first block."), Delete(3, "First paragraph."))
    assert read_doc_comments(path)[0]["block"] == 2


def test_a_comment_whose_block_text_changed_is_detached_and_kept(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    add_doc_comment(path, block=1, text="Check this", author="Ana", sent=False)

    _edit(path, Replace(1, "First paragraph.", "Rewritten."))
    read = read_doc_comments(path)

    assert read[0]["block"] is None and read[0]["detached"] is True
    assert read[0]["text"] == "Check this"


def test_with_the_same_text_twice_the_comment_stays_on_the_copy_it_was_made_on(
    tmp_path: Path,
) -> None:
    path = _doc(tmp_path, SOURCE + "\nFirst paragraph.\n")
    add_doc_comment(path, block=3, text="The second copy", author="Ana", sent=False)

    _edit(path, Insert(-1, "At the top."))

    assert read_doc_comments(path)[0]["block"] == 4


def test_a_reply_a_resolve_and_a_delete(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    comment = add_doc_comment(path, block=0, text="Title?", author="Ana", sent=True)

    reply_to_doc_comment(path, comment["id"], text="Renamed.", author="coscribe")
    resolve_doc_comment(path, comment["id"], True)
    read = read_doc_comments(path)[0]
    assert [r["author"] for r in read["replies"]] == ["coscribe"]
    assert read["resolved"] is True

    resolve_doc_comment(path, comment["id"], False)
    assert read_doc_comments(path)[0]["resolved"] is False
    delete_doc_comment(path, comment["id"])
    assert read_doc_comments(path) == []


@pytest.mark.parametrize(
    ("block", "text", "message"),
    [(9, "x", "no block 9"), (-1, "x", "no block -1"), (0, "   ", "needs some text"),
     (0, "x" * 4001, "4000")],
)  # fmt: skip
def test_a_comment_that_cannot_be_made_says_why(
    tmp_path: Path, block: int, text: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        add_doc_comment(_doc(tmp_path), block=block, text=text, author="Ana", sent=False)


def test_an_unknown_comment_and_a_file_that_is_not_a_doc(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    for act in (
        lambda: reply_to_doc_comment(path, "nope", text="x", author="a"),
        lambda: resolve_doc_comment(path, "nope", True),
        lambda: delete_doc_comment(path, "nope"),
    ):
        with pytest.raises(DocCommentNotFound):
            act()
    with pytest.raises(NotADoc):
        read_doc_comments(_doc(tmp_path, "# Just notes\n"))


def test_a_damaged_store_counts_as_no_comments_and_is_replaced_by_the_next_one(
    tmp_path: Path,
) -> None:
    path = _doc(tmp_path)
    folder = tmp_path / "plan.doc"
    folder.mkdir()
    (folder / "comments.json").write_text("not json", encoding="utf-8")
    assert read_doc_comments(path) == []

    add_doc_comment(path, block=0, text="Fresh", author="Ana", sent=False)

    assert (
        json.loads((folder / "comments.json").read_text(encoding="utf-8"))["comments"][0]["text"]
        == "Fresh"
    )
