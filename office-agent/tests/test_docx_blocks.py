"""The Docs editor's reader and writer (decision 0019): a .docx as blocks, and a save that rewrites
only the blocks the person changed, leaving comments, tracked changes and the rest as they were."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from lxml import etree

from coscribe.tools.office.document_tools import build_document_tools
from coscribe.tools.office.docx import (
    BlocksRefused,
    DocChanged,
    read_doc_blocks,
    save_doc_blocks,
)

CONTENT = """\
# Service agreement

## Price

The total price is **100 dollars**, due within 30 days. {{comment: Final price?}}

## Term

The agreement runs for one year, see *schedule A*.

- first point
- second point

1. step one
2. step two

| item | cost |
|---|---|
| a | 1 |
| b | 2 |
"""
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _tools(root: Path) -> dict[str, Any]:
    return {tool.__name__: tool for tool in build_document_tools(root)}


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    _tools(tmp_path)["write_docx"](path="d.docx", content=CONTENT, comment_author="Ana")
    return tmp_path / "d.docx"


def _blocks(path: Path) -> tuple[str, list[dict[str, Any]]]:
    read = read_doc_blocks(path)
    return read["version"], read["blocks"]


def _by_text(blocks: list[dict[str, Any]], text: str) -> dict[str, Any]:
    return next(b for b in blocks if any(text in r["t"] for r in b.get("runs", [])))


def _paragraphs(path: Path) -> list[bytes]:
    tree = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    return [etree.tostring(p, method="c14n") for p in tree.iter(f"{W}p")]


def _canonical(name: str, data: bytes) -> Any:
    if not name.endswith((".xml", ".rels")):
        return data
    root = etree.fromstring(data)
    if name == "[Content_Types].xml":  # python-docx lists the same entries in its own order
        return sorted(etree.tostring(child, method="c14n") for child in root)
    return etree.tostring(root, method="c14n")


def _parts(path: Path) -> dict[str, Any]:
    """Every part but the body, as XML: python-docx writes the same XML its own way."""
    z = zipfile.ZipFile(path)
    return {n: _canonical(n, z.read(n)) for n in z.namelist() if n != "word/document.xml"}


def test_a_document_reads_as_blocks_with_what_the_editor_cannot_change_locked(doc: Path) -> None:
    _, blocks = _blocks(doc)
    kinds = [(b["kind"], b.get("level")) for b in blocks]
    assert kinds[:3] == [("title", None), ("heading", 2), ("locked", None)]
    assert blocks[2]["what"] == "comment" and "100 dollars" in blocks[2]["text"]
    assert ("bullet", 1) in kinds and ("number", 1) in kinds and kinds[-1] == ("table", None)
    schedule = _by_text(blocks, "schedule A")
    assert [r for r in schedule["runs"] if r.get("i")] == [{"t": "schedule A", "i": True}]
    table = blocks[-1]
    assert table["header"] and table["rows"][1] == [[{"t": "a"}], [{"t": "1"}]]


def test_saving_what_was_read_changes_no_paragraph_and_no_other_part(doc: Path) -> None:
    before_paragraphs, before_parts = _paragraphs(doc), _parts(doc)
    version, blocks = _blocks(doc)
    save_doc_blocks(doc, version, blocks)
    assert _paragraphs(doc) == before_paragraphs
    assert _parts(doc) == before_parts


def test_a_changed_paragraph_is_the_only_one_rewritten(doc: Path) -> None:
    before = _paragraphs(doc)
    version, blocks = _blocks(doc)
    term = _by_text(blocks, "one year")
    term["runs"] = [{"t": "The agreement runs for "}, {"t": "two", "b": True}, {"t": " years."}]
    result = save_doc_blocks(doc, version, blocks)
    after = _paragraphs(doc)
    edited = next(i for i, p in enumerate(before) if b"one year" in p)
    assert [i for i, (x, y) in enumerate(zip(before, after, strict=True)) if x != y] == [edited]
    assert _by_text(result["blocks"], "two")["runs"][1] == {"t": "two", "b": True}


def test_comments_and_tracked_changes_survive_an_edit_elsewhere(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    tools["write_docx"](path="r.docx", content=CONTENT, comment_author="Ana")
    tools["insert_docx_text"](path="r.docx", text=" (extended)", context_before="30 days")
    tools["delete_docx_text"](path="r.docx", text="one year")
    path = tmp_path / "r.docx"
    version, blocks = _blocks(path)
    assert {b["what"] for b in blocks if b["kind"] == "locked"} >= {"comment", "tracked change"}
    first = blocks[1]
    first["runs"] = [{"t": "Cost"}]
    save_doc_blocks(path, version, blocks)
    document = zipfile.ZipFile(path).read("word/document.xml").decode()
    assert "<w:ins " in document and "<w:del " in document and "commentRangeStart" in document
    assert "word/comments.xml" in zipfile.ZipFile(path).namelist()


def test_a_locked_block_is_kept_whatever_the_editor_sends_for_it(doc: Path) -> None:
    before = _paragraphs(doc)
    version, blocks = _blocks(doc)
    blocks[2] = {**blocks[2], "text": "ignored", "kind": "locked", "runs": [{"t": "nope"}]}
    save_doc_blocks(doc, version, blocks)
    assert _paragraphs(doc) == before


def test_changing_a_kind_new_blocks_and_deletions(doc: Path) -> None:
    version, blocks = _blocks(doc)
    first = _by_text(blocks, "first point")
    second = _by_text(blocks, "second point")
    first["kind"] = "number"
    blocks.remove(second)
    heading = {"kind": "heading", "level": 3, "runs": [{"t": "Appendix"}]}
    quote = {"kind": "quote", "runs": [{"t": "A quoted line"}]}
    note = {
        "kind": "paragraph",
        "runs": [{"t": "tab\there"}, {"t": " site", "link": "https://example.com/a"}],
    }
    blocks[blocks.index(first) :] = [
        first,
        heading,
        quote,
        note,
        *blocks[blocks.index(first) + 1 :],
    ]
    result = save_doc_blocks(doc, version, blocks)
    read = result["blocks"]
    assert _by_text(read, "first point")["kind"] == "number"
    assert not any("second point" in r["t"] for b in read for r in b.get("runs", []))
    assert _by_text(read, "Appendix")["level"] == 3
    assert _by_text(read, "A quoted line")["kind"] == "quote"
    linked = _by_text(read, "site")
    assert linked["runs"][1] == {"t": " site", "link": "https://example.com/a"}
    assert linked["runs"][0]["t"] == "tab\there"
    paragraph = Document(doc).paragraphs
    assert any(p.style.name == "Heading 3" and p.text == "Appendix" for p in paragraph)


def test_table_cells_rows_and_columns(doc: Path) -> None:
    version, blocks = _blocks(doc)
    table = blocks[-1]
    table["rows"][1][1] = [{"t": "10"}]
    table["rows"].append([[{"t": "c"}], [{"t": "3"}]])
    version = save_doc_blocks(doc, version, blocks)["version"]
    _, blocks = _blocks(doc)
    assert [[c[0]["t"] for c in row] for row in blocks[-1]["rows"]] == [
        ["item", "cost"],
        ["a", "10"],
        ["b", "2"],
        ["c", "3"],
    ]
    blocks[-1]["rows"] = [[row[0]] for row in blocks[-1]["rows"]]
    save_doc_blocks(doc, version, blocks)
    _, blocks = _blocks(doc)
    assert [row[0][0]["t"] for row in blocks[-1]["rows"]] == ["item", "a", "b", "c"]
    assert all(len(row) == 1 for row in blocks[-1]["rows"])
    assert len(Document(doc).tables[0].columns) == 1


def test_a_new_table_and_a_list_that_restarts(doc: Path) -> None:
    version, blocks = _blocks(doc)
    blocks.append(
        {
            "kind": "table",
            "header": True,
            "rows": [[[{"t": "x"}], [{"t": "y"}]], [[{"t": "1"}], [{"t": "2"}]]],
        }
    )
    blocks.append({"kind": "number", "level": 1, "runs": [{"t": "again"}]})
    result = save_doc_blocks(doc, version, blocks)
    assert [b["kind"] for b in result["blocks"]][-3:] == ["table", "table", "number"]


def test_a_save_over_a_newer_file_is_refused(doc: Path) -> None:
    version, blocks = _blocks(doc)
    changed = Document(doc)
    changed.add_paragraph("added in Word")
    changed.save(doc)
    with pytest.raises(DocChanged):
        save_doc_blocks(doc, version, blocks)


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "paragraph", "runs": [{"t": "x", "link": "javascript:alert(1)"}]},
        {"kind": "heading", "level": 9, "runs": []},
        {"kind": "table", "rows": [[[{"t": "a"}]], [[{"t": "b"}], [{"t": "c"}]]]},
        {"kind": "mystery"},
        "text",
    ],
)
def test_a_block_that_cannot_be_written_is_refused(doc: Path, bad: Any) -> None:
    version, blocks = _blocks(doc)
    before = doc.read_bytes()
    with pytest.raises(BlocksRefused):
        save_doc_blocks(doc, version, [*blocks, bad])
    assert doc.read_bytes() == before


def test_a_missing_style_is_said_plainly(tmp_path: Path) -> None:
    plain = Document()
    plain.add_paragraph("hello")
    quote = plain.styles["Quote"].element
    quote.getparent().remove(quote)
    path = tmp_path / "p.docx"
    plain.save(path)
    version, blocks = _blocks(path)
    blocks.append({"kind": "quote", "runs": [{"t": "q"}]})
    with pytest.raises(BlocksRefused, match="no 'Quote' style"):
        save_doc_blocks(path, version, blocks)


def test_contents_pictures_and_charts_are_locked_and_a_save_leaves_them_alone(
    tmp_path: Path,
) -> None:
    from PIL import Image

    Image.new("RGB", (40, 20), "red").save(tmp_path / "pic.png")
    tools = _tools(tmp_path)
    tools["write_docx"](path="m.docx", content="# T\n\n[TOC]\n\n## One\n\ntext\n\n## Two\n\nmore\n")
    tools["add_docx_image"](path="m.docx", image_path="pic.png", after_text="text")
    tools["add_docx_chart"](
        path="m.docx",
        chart_type="bar",
        data="| x | y |\n|---|---|\n| a | 1 |\n| b | 2 |",
        after_text="more",
    )
    path = tmp_path / "m.docx"
    before = _paragraphs(path)
    version, blocks = _blocks(path)
    locked = {b["what"] for b in blocks if b["kind"] == "locked"}
    assert {"field", "image or drawing"} <= locked
    save_doc_blocks(path, version, blocks)
    assert _paragraphs(path) == before
    assert Document(path).paragraphs  # still opens
