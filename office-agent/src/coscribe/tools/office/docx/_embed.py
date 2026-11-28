"""A file put inside a Word document as an icon that opens it: the file's bytes travel in the
document as an OLE Package (`_ole.py`), shown as a page icon with the file's name (`_icon.py`),
written as the `w:object` Word itself writes for "insert object from file, display as icon"."""

from __future__ import annotations

import copy
from typing import Any

from ._icon import icon_emf
from ._ole import ole_package

_V = "urn:schemas-microsoft-com:vml"
_O = "urn:schemas-microsoft-com:office:office"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
# The picture-frame shape type every embedded object's VML shape refers to.
_SHAPETYPE = (
    f'<v:shapetype xmlns:v="{_V}" xmlns:o="{_O}" id="_x0000_t75" coordsize="21600,21600" '
    'o:spt="75" o:preferrelative="t" path="m@4@5l@4@11@9@11@9@5xe" filled="f" stroked="f">'
    '<v:stroke joinstyle="miter"/><v:formulas>'
    + "".join(
        f'<v:f eqn="{eqn}"/>'
        for eqn in (
            "if lineDrawn pixelLineWidth 0",
            "sum @0 1 0",
            "sum 0 0 @1",
            "prod @2 1 2",
            "prod @3 21600 pixelWidth",
            "prod @3 21600 pixelHeight",
            "sum @0 0 1",
            "prod @6 1 2",
            "prod @7 21600 pixelWidth",
            "sum @8 21600 0",
            "prod @7 21600 pixelHeight",
            "sum @10 21600 0",
        )
    )
    + '</v:formulas><v:path o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/>'
    '<o:lock v:ext="edit" aspectratio="t"/></v:shapetype>'
)


def _text_of(element: Any) -> str:
    return "".join(t.text or "" for t in element.iter(f"{{{_W}}}t")).strip()


def _cell_beside(document: Any, label: str) -> tuple[Any, Any, int]:
    """The table cell to the right of the one whose text is `label`, with its table and column."""
    found = []
    for table in document.tables:
        for row in table.rows:
            cells = list(row.cells)
            for index, cell in enumerate(cells[:-1]):
                text = cell.text.strip()
                if text == label.strip() and cells[index + 1]._tc is not cell._tc:
                    found.append((table, cells[index + 1], index + 1))
    if not found:
        raise ValueError(f"No table cell reads {label!r} with a cell to its right.")
    if len(found) > 1:
        raise ValueError(f"{len(found)} table cells read {label!r}; the file was not embedded.")
    return found[0][1], found[0][0], found[0][2]


def _column_font(table: Any, column: int, skip: Any) -> Any:
    """The run format of the column's text in the nearest row that has some, so the icon's line
    sits in the column like its neighbours rather than like its header."""
    rows = [list(row.cells) for row in table.rows]
    at = next(i for i, cells in enumerate(rows) if any(c._tc is skip for c in cells))
    nearest = sorted(range(len(rows)), key=lambda i: (abs(i - at), i > at))
    for index in nearest:
        cells = rows[index]
        if column >= len(cells) or cells[column]._tc is skip:
            continue
        for run in cells[column]._tc.iter(f"{{{_W}}}r"):
            props = run.find(f"{{{_W}}}rPr")
            if props is not None and _text_of(run):
                return props
    return None


def _target_paragraph(document: Any, after_text: str, beside: str) -> Any:
    """The paragraph that will hold the icon: the first empty one of the cell beside `beside`
    (a form's blank answer), a new one after the paragraph `after_text` names, or a new last."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    if beside:
        cell, table, column = _cell_beside(document, beside)
        empty = [p for p in cell.paragraphs if not p.text.strip() and not _has_object(p)]
        paragraph = empty[0] if empty else cell.add_paragraph()
        font = _column_font(table, column, cell._tc)
    else:
        paragraph = document.add_paragraph()
        font = None
        if after_text:
            anchor = _paragraph_named(document, after_text, paragraph)
            anchor._p.addnext(paragraph._p)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return paragraph, font


def _has_object(paragraph: Any) -> bool:
    element = paragraph._p
    return any(True for _ in element.iter(f"{{{_W}}}object", f"{{{_W}}}drawing"))


def _paragraph_named(document: Any, after_text: str, skip: Any) -> Any:
    others = [p for p in document.paragraphs if p._p is not skip._p]
    wanted = after_text.strip()
    matches = [p for p in others if p.text.strip() == wanted] or [
        p for p in others if wanted in p.text
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{len(matches)} paragraphs contain {after_text!r}; give text that names one."
        )
    return matches[0]


def _unused_shape_id(document: Any) -> int:
    xml = document.element.xml
    number = 1025
    while f"_x0000_i{number}" in xml:
        number += 1
    return number


def embed_file(
    document: Any, name: str, data: bytes, after_text: str, beside: str
) -> dict[str, Any]:
    """Put `data`, a file named `name`, into `document` as an icon that opens it."""
    from docx.opc.constants import CONTENT_TYPE, RELATIONSHIP_TYPE
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part
    from lxml import etree

    paragraph, font = _target_paragraph(document, after_text, beside)
    package = document.part.package
    taken = {str(part.partname) for part in package.iter_parts()}
    index = 1
    while f"/word/embeddings/oleObject{index}.bin" in taken:
        index += 1
    ole_part = Part(
        PackURI(f"/word/embeddings/oleObject{index}.bin"),
        CONTENT_TYPE.OFC_OLE_OBJECT,
        ole_package(name, data),
        package,
    )
    icon, width, height = icon_emf(name)
    image_index = 1
    while f"/word/media/embedIcon{image_index}.emf" in taken:
        image_index += 1
    icon_part = Part(
        PackURI(f"/word/media/embedIcon{image_index}.emf"), CONTENT_TYPE.X_EMF, icon, package
    )
    ole_rid = document.part.relate_to(ole_part, RELATIONSHIP_TYPE.OLE_OBJECT)
    icon_rid = document.part.relate_to(icon_part, RELATIONSHIP_TYPE.IMAGE)

    number = _unused_shape_id(document)
    shape_id = f"_x0000_i{number}"
    shapetype = "" if "_x0000_t75" in document.element.xml else _SHAPETYPE
    object_xml = (
        f'<w:object xmlns:w="{_W}" xmlns:v="{_V}" xmlns:o="{_O}" xmlns:r="{_R}" '
        f'w:dxaOrig="{round(width * 20)}" w:dyaOrig="{round(height * 20)}">'
        f"{shapetype}"
        f'<v:shape id="{shape_id}" type="#_x0000_t75" o:ole="" '
        f'style="width:{width:.1f}pt;height:{height:.1f}pt">'
        f'<v:imagedata r:id="{icon_rid}" o:title=""/></v:shape>'
        f'<o:OLEObject Type="Embed" ProgID="Package" ShapeID="{shape_id}" DrawAspect="Icon" '
        f'ObjectID="_{1_500_000_000 + number}" r:id="{ole_rid}"/>'
        "</w:object>"
    )
    run = paragraph.add_run()
    if font is not None:
        run._r.insert(0, copy.deepcopy(font))
    run._r.append(etree.fromstring(object_xml))
    return {
        "embedded": name,
        "bytes_embedded": len(data),
        "icon_size_pt": [width, height],
        "note": (
            "Done as Word does it: clicking the icon (a double-click, as for any object in "
            "Word) opens the file, from inside the document. Leave it as it is: no hyperlink to "
            "the file on disk as well (it breaks once the document is sent on its own), no "
            "resizing, no text about it, and keep the blank lines beside it, unless the person "
            "asked for that."
        ),
    }
