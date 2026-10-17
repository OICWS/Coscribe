"""Canonical text of a `.docx`, for golden tests that must be byte-identical across runs.

The generic parts (zip order, attribute order, whitespace, the core-properties timestamps, a
chart's embedded workbook) come from `pptx_canonical`. What a Word file adds are values the tools
write fresh on every build: the random `w14:paraId` Word uses to name a paragraph, and the
`w:date` of a comment or a tracked change. Both are blanked; a probe building one document in two
processes found nothing else that varies.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from lxml import etree

from .pptx_canonical import _PACKAGE_SUFFIXES, _VOLATILE_CORE_PROPERTIES, _sort_attributes
from .pptx_canonical import canonical_part as _canonical_member

_XML_SUFFIXES = (".xml", ".rels")
_EMBEDDINGS = "word/embeddings/"
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
# paraId is random per paragraph; w:date is the time of the edit or comment.
_W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
# A comment thread names its paragraphs with random ids and points a reply at its parent by
# them. They are renumbered in order of appearance so the link stays visible.
_THREAD_IDS = (f"{{{_W15}}}paraId", f"{{{_W15}}}paraIdParent")
_VOLATILE_ATTRIBUTES = {f"{{{_W14}}}paraId", f"{{{_W14}}}textId", f"{{{_W}}}date"}


def _blank_volatile_attributes(root: etree._Element) -> None:
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        for key in _VOLATILE_ATTRIBUTES.intersection(node.attrib):
            node.set(key, "<normalised>")
    numbered: dict[str, str] = {}
    for node in root.iter():
        if not isinstance(node.tag, str):
            continue
        for key in _THREAD_IDS:
            if key in node.attrib:
                node.set(key, numbered.setdefault(node.get(key, ""), f"<id{len(numbered) + 1}>"))


def canonical_part(name: str, data: bytes) -> str:
    """The canonical text of one zip member of a `.docx`."""
    if name.startswith(_EMBEDDINGS) and name.endswith(_PACKAGE_SUFFIXES):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return "".join(
                f"----- {inner}\n{canonical_part(inner, archive.read(inner))}"
                for inner in sorted(archive.namelist())
            )
    if not name.endswith(_XML_SUFFIXES):
        return _canonical_member(name, data)
    root = etree.fromstring(data, etree.XMLParser(remove_blank_text=True))
    if name == "docProps/core.xml":
        for node in list(root):
            if node.tag in _VOLATILE_CORE_PROPERTIES:
                node.text = "<normalised>"
    _blank_volatile_attributes(root)
    _sort_attributes(root)
    return etree.tostring(root, pretty_print=True, encoding="unicode")


def canonical_parts(path: Path) -> dict[str, str]:
    """Every member of the zip at `path`, by name, as canonical text."""
    with zipfile.ZipFile(path) as archive:
        return {
            name: canonical_part(name, archive.read(name)) for name in sorted(archive.namelist())
        }
