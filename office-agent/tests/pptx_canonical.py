"""Canonical text of an Office file, for golden tests that must be byte-identical across runs.

A `.pptx` is a zip of XML parts. Two builds of the same deck can differ in ways that say
nothing about what the deck is: the zip's member order and timestamps, the order an XML
writer emits attributes in, insignificant whitespace, and the creation and modification
times in `docProps/core.xml`, the deck's own and that of an Office package embedded in it (the
workbook behind a chart, written with the time of the build). Those are removed here.
Everything else is kept, so a difference that remains is a real difference in the generated
document.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

from lxml import etree

_XML_SUFFIXES = (".xml", ".rels")
_EMBEDDINGS = "ppt/embeddings/"
_PACKAGE_SUFFIXES = (".xlsx", ".docx", ".pptx")

# Only the per-run timestamps: a title, an author or a revision count that changes is a change
# in what the tools wrote, and must show.
_VOLATILE_CORE_PROPERTIES = {
    "{http://purl.org/dc/terms/}created",
    "{http://purl.org/dc/terms/}modified",
}


def _sort_attributes(element: etree._Element) -> None:
    for node in element.iter():
        if not isinstance(node.tag, str):
            continue
        items = sorted(node.attrib.items())
        node.attrib.clear()
        for key, value in items:
            node.set(key, value)


def _embedded_package(data: bytes) -> str:
    # A chart's data travels as a whole Office package inside the deck; its own docProps carry
    # the build time, so it is opened and canonicalised by the same rules instead of hashed.
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return "".join(
            f"----- {inner}\n{canonical_part(inner, archive.read(inner))}"
            for inner in sorted(archive.namelist())
        )


def canonical_part(name: str, data: bytes) -> str:
    """The canonical text of one zip member: indented XML, an embedded Office package member by
    member, or a size and hash for other binaries."""
    if name.startswith(_EMBEDDINGS) and name.endswith(_PACKAGE_SUFFIXES):
        return _embedded_package(data)
    if not name.endswith(_XML_SUFFIXES):
        return f"<binary {len(data)} bytes sha256={hashlib.sha256(data).hexdigest()}>\n"
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(data, parser)
    if name == "docProps/core.xml":
        for node in list(root):
            if node.tag in _VOLATILE_CORE_PROPERTIES:
                node.text = "<normalised>"
    _sort_attributes(root)
    return etree.tostring(root, pretty_print=True, encoding="unicode")


def canonical_parts(path: Path) -> dict[str, str]:
    """Every member of the zip at `path`, by name, as canonical text."""
    with zipfile.ZipFile(path) as archive:
        return {
            name: canonical_part(name, archive.read(name)) for name in sorted(archive.namelist())
        }


def canonical_text(path: Path) -> str:
    """One readable document for the whole file, members in name order."""
    return "".join(f"===== {name}\n{text}" for name, text in canonical_parts(path).items())
