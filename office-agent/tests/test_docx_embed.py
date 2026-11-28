"""A file put inside a Word document opens from its icon: its bytes travel in the document as an
OLE Package, shown as an icon with the file's name, in the place the person named."""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.shared import Pt
from lxml import etree

from coscribe.tools.office.docx import DocxToolkit
from coscribe.tools.office.docx._icon import icon_emf
from coscribe.tools.office.docx._ole import ole_package

_END = 0xFFFFFFFE


def _streams(blob: bytes) -> dict[str, bytes]:
    """Read a compound file the way any reader does: header, DIFAT, FAT, directory, chains."""
    assert blob[:8] == bytes.fromhex("d0cf11e0a1b11ae1")
    fat_count, dir_start = struct.unpack_from("<II", blob, 44)
    mini_fat_start, _, difat_start, difat_count = struct.unpack_from("<IIII", blob, 60)

    def sector(n: int) -> bytes:
        return blob[512 + n * 512 : 1024 + n * 512]

    fat_sectors = list(struct.unpack_from("<109I", blob, 76))
    at = difat_start
    for _ in range(difat_count):
        ids = struct.unpack("<128I", sector(at))
        fat_sectors += ids[:127]
        at = ids[127]
    fat: list[int] = []
    for n in fat_sectors[:fat_count]:
        fat += struct.unpack("<128I", sector(n))

    def chain(start: int, table: list[int]) -> list[int]:
        out = []
        while start != _END:
            out.append(start)
            start = table[start]
        return out

    directory = b"".join(sector(n) for n in chain(dir_start, fat))
    entries = []
    for i in range(len(directory) // 128):
        raw = directory[i * 128 : (i + 1) * 128]
        length, kind = struct.unpack_from("<HB", raw, 64)
        start, size = struct.unpack_from("<IQ", raw, 116)
        entries.append((raw[: max(length - 2, 0)].decode("utf-16-le"), kind, start, size))
    root = entries[0]
    mini = b"".join(sector(n) for n in chain(root[2], fat)) if root[3] else b""
    mini_fat: list[int] = []
    for n in chain(mini_fat_start, fat) if mini_fat_start != _END else []:
        mini_fat += struct.unpack("<128I", sector(n))
    out = {}
    for name, kind, start, size in entries[1:]:
        if kind != 2:
            continue
        if size < 4096:
            data = b"".join(mini[n * 64 : n * 64 + 64] for n in chain(start, mini_fat))
        else:
            data = b"".join(sector(n) for n in chain(start, fat))
        out[name] = data[:size]
    return out


@pytest.mark.parametrize("size", [0, 10, 5000, 8_000_000])
def test_a_package_holds_the_file_whole_and_named(size: int):
    data = bytes(range(256)) * (size // 256) + b"x" * (size % 256)
    streams = _streams(ole_package("计划.pptx", data))
    assert set(streams) == {"\x01CompObj", "\x01Ole", "\x01Ole10Native"}
    native = streams["\x01Ole10Native"]
    assert struct.unpack_from("<I", native)[0] == len(native) - 4
    assert data in native
    assert "计划.pptx".encode("utf-16-le") in native
    assert b"OLE Package" in streams["\x01CompObj"]


def test_a_large_file_ends_near_the_end_of_the_package():
    """A reader that finds the embedded file by looking for a zip from the end still finds it."""
    data = b"PK" + b"\0" * 3_000_000
    blob = ole_package("deck.pptx", data)
    assert len(blob) - (blob.rindex(data) + len(data)) < 1024


def _emf_texts(blob: bytes) -> list[str]:
    texts, pos = [], 0
    while pos < len(blob):
        kind, size = struct.unpack_from("<II", blob, pos)
        if kind == 84:
            chars, offset = struct.unpack_from("<II", blob, pos + 44)
            texts.append(blob[pos + offset : pos + offset + 2 * chars].decode("utf-16-le"))
        pos += size
    return texts


def test_the_icon_shows_the_whole_name_and_the_kind():
    blob, width, height = icon_emf("青梧谷灵MR共创计划.pptx")
    assert struct.unpack_from("<I", blob, 40)[0] == 0x464D4520
    assert struct.unpack_from("<I", blob, 48)[0] == len(blob)
    texts = _emf_texts(blob)
    assert texts[0] == "P"
    assert "".join(texts[1:]) == "青梧谷灵MR共创计划.pptx"
    assert len(texts) == 3 and 60 < width < 120 and 50 < height < 90
    long_name = "a report " * 10 + ".pdf"
    assert len(_emf_texts(icon_emf(long_name)[0])) == 4  # the badge, then three lines at most


def _form(path: Path) -> None:
    document = Document()
    document.add_paragraph("Application")
    table = document.add_table(rows=3, cols=2)
    labels = [("Item", "Content"), ("Summary", "A short plan."), ("Materials", "")]
    for row, (label, content) in zip(table.rows, labels, strict=True):
        row.cells[0].text = label
        if content:
            run = row.cells[1].paragraphs[0].add_run(content)
            run.font.size = Pt(9)
            run.font.name = "Noto Serif"
    table.rows[0].cells[1].paragraphs[0].runs[0].font.size = Pt(14)
    table.rows[2].cells[1].add_paragraph()
    document.add_paragraph("Signed")
    document.save(str(path))


def _toolkit(tmp_path: Path) -> DocxToolkit:
    _form(tmp_path / "form.docx")
    (tmp_path / "plan.pptx").write_bytes(b"PK\x03\x04 a deck")
    return DocxToolkit(tmp_path)


def test_a_file_goes_into_the_cell_beside_a_label_and_opens_from_its_icon(tmp_path: Path):
    toolkit = _toolkit(tmp_path)

    result = toolkit.embed_docx_file("form.docx", "plan.pptx", in_cell_beside="Materials")

    assert result["embedded"] == "plan.pptx"
    document = Document(str(tmp_path / "form.docx"))
    cell = document.tables[0].rows[2].cells[1]
    obj = cell._tc.xpath(".//w:object")
    assert len(obj) == 1
    xml = etree.tostring(obj[0]).decode()
    assert 'ProgID="Package"' in xml and 'DrawAspect="Icon"' in xml and 'Type="Embed"' in xml
    paragraph = next(p for p in cell.paragraphs if p._p.xpath(".//w:object"))
    assert paragraph.alignment == 1  # centred
    assert paragraph.runs[0].font.size == Pt(9)  # the column's text, not its header
    assert len(cell.paragraphs) == 2  # the blank line was used, not a new one added
    with zipfile.ZipFile(tmp_path / "form.docx") as package:
        names = package.namelist()
        rels = package.read("word/_rels/document.xml.rels").decode()
        types = package.read("[Content_Types].xml").decode()
        embedded = package.read("word/embeddings/oleObject1.bin")
    assert "word/media/embedIcon1.emf" in names
    assert "relationships/oleObject" in rels and 'Extension="emf"' in types
    assert b"PK\x03\x04 a deck" in _streams(embedded)["\x01Ole10Native"]


def test_a_file_goes_after_a_paragraph_and_a_second_one_gets_its_own_parts(tmp_path: Path):
    toolkit = _toolkit(tmp_path)
    toolkit.embed_docx_file("form.docx", "plan.pptx", after_text="Application")
    toolkit.embed_docx_file("form.docx", "plan.pptx")

    document = Document(str(tmp_path / "form.docx"))
    body = document.element.body
    objects = body.xpath(".//w:object")
    assert len(objects) == 2
    assert document.paragraphs[1]._p.xpath(".//w:object")
    assert document.paragraphs[-1]._p.xpath(".//w:object")
    shapes = {o.find("{urn:schemas-microsoft-com:vml}shape").get("id") for o in objects}
    assert len(shapes) == 2
    with zipfile.ZipFile(io.BytesIO((tmp_path / "form.docx").read_bytes())) as package:
        assert {"word/embeddings/oleObject1.bin", "word/embeddings/oleObject2.bin"} <= set(
            package.namelist()
        )


@pytest.mark.parametrize(
    ("place", "message"),
    [
        ({"in_cell_beside": "Nowhere"}, "No table cell"),
        ({"after_text": "Missing"}, "0 paragraphs"),
        ({"after_text": "Application", "in_cell_beside": "Materials"}, "not both"),
    ],
)
def test_a_place_that_names_nothing_or_two_things_is_refused(
    tmp_path: Path, place: dict[str, str], message: str
):
    toolkit = _toolkit(tmp_path)
    before = (tmp_path / "form.docx").read_bytes()
    with pytest.raises(ValueError, match=message):
        toolkit.embed_docx_file("form.docx", "plan.pptx", **place)
    assert (tmp_path / "form.docx").read_bytes() == before
