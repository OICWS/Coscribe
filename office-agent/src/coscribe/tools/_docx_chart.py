"""A native, editable chart inside a Word document.

python-docx has no chart support, but python-pptx's chart XML writer and
embedded-workbook builder produce exactly the parts Word expects; this
only has to add them to the docx package and point an inline drawing at
the chart part. A native chart (not a picture) stays editable in Word and
needs no plotting library, which the packaged app doesn't ship.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from lxml import etree

_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

_CHART_CT = "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"
_XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# The writer's default text is 18 pt, sized for a slide; body text in a
# document is 10-11 pt.
_CHART_TEXT_SIZE = "1000"


def _paint_series(root: Any, chart_type: str, points: int, colors: Sequence[str]) -> None:
    """Each series (each slice, on a pie) in `colors` (RRGGBB), in order."""

    def fill(color: str) -> str:
        return f'<a:solidFill xmlns:a="{_A}"><a:srgbClr val="{color}"/></a:solidFill>'

    for index, series in enumerate(root.iter(f"{{{_C}}}ser")):
        color = colors[index % len(colors)]
        look = (
            f'<a:ln xmlns:a="{_A}" w="28575" cap="rnd">{fill(color)}<a:round/></a:ln>'
            if chart_type == "line"
            else fill(color)
        )
        properties = etree.fromstring(f'<c:spPr xmlns:c="{_C}">{look}</c:spPr>')
        anchor = series.find(f"{{{_C}}}tx")
        if anchor is None:
            anchor = series.find(f"{{{_C}}}order")
        anchor.addnext(properties)
        if chart_type != "pie":
            continue
        # Schema order: a slice's colour (dPt) goes before the labels and the categories.
        before = series.find(f"{{{_C}}}dLbls")
        if before is None:
            before = series.find(f"{{{_C}}}cat")
        for point in range(points):
            before.addprevious(
                etree.fromstring(
                    f'<c:dPt xmlns:c="{_C}"><c:idx val="{point}"/><c:bubble3D val="0"/>'
                    f"<c:spPr>{fill(colors[point % len(colors)])}</c:spPr></c:dPt>"
                )
            )


def _chart_xml(
    chart_type: str,
    categories: list[str],
    series: dict[str, list[float]],
    title: str,
    fonts: tuple[str, str] | None = None,
    colors: Sequence[str] = (),
) -> tuple[bytes, bytes]:
    from pptx.chart.data import CategoryChartData
    from pptx.chart.xmlwriter import ChartXmlWriter
    from pptx.enum.chart import XL_CHART_TYPE

    chart_data = CategoryChartData()  # type: ignore[no-untyped-call]
    chart_data.categories = categories
    for name, values in series.items():
        chart_data.add_series(name, values)  # type: ignore[no-untyped-call]
    xl_type = {
        "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
        "line": XL_CHART_TYPE.LINE,
        "pie": XL_CHART_TYPE.PIE,
    }[chart_type]
    root = etree.fromstring(ChartXmlWriter(xl_type, chart_data).xml.encode("utf-8"))  # type: ignore[no-untyped-call]
    ns = {"c": _C, "a": _A}

    chart = root.find("c:chart", ns)
    assert chart is not None
    for size in root.iterfind("c:txPr//a:defRPr", ns):
        size.set("sz", _CHART_TEXT_SIZE)

    if title:
        title_xml = (
            f'<c:title xmlns:c="{_C}" xmlns:a="{_A}"><c:tx><c:rich><a:bodyPr/><a:p>'
            f'<a:pPr><a:defRPr sz="1200" b="1"/></a:pPr><a:r><a:rPr lang="en-US" sz="1200" b="1"/>'
            f'<a:t></a:t></a:r></a:p></c:rich></c:tx><c:overlay val="0"/></c:title>'
        )
        title_el = etree.fromstring(title_xml)
        title_el.find(".//a:t", ns).text = title
        chart.insert(0, title_el)
        chart.find("c:autoTitleDeleted", ns).set("val", "0")
    else:
        chart.find("c:autoTitleDeleted", ns).set("val", "1")

    # Without a typeface a reader without the document's theme falls back to a serif font.
    if fonts is not None:
        for run_properties in root.iter(f"{{{_A}}}defRPr", f"{{{_A}}}rPr"):
            for tag, face in (("latin", fonts[0]), ("ea", fonts[1])):
                etree.SubElement(run_properties, f"{{{_A}}}{tag}").set("typeface", face)

    # A column chart reads by the height of its bars; an axis that starts near the smallest value
    # makes a 7% rise look like a tripling.
    scaling = chart.find("c:plotArea/c:valAx/c:scaling", ns)
    if (
        chart_type == "bar"
        and scaling is not None
        and min((v for vs in series.values() for v in vs), default=0) >= 0
    ):
        etree.SubElement(scaling, f"{{{_C}}}min").set("val", "0")

    # Axis labels only; the values themselves keep every decimal.
    values = [abs(v) for vs in series.values() for v in vs]
    value_axis = chart.find("c:plotArea/c:valAx", ns)
    if value_axis is not None and values and max(values) >= 1000:
        number_format = etree.fromstring(
            f'<c:numFmt xmlns:c="{_C}" formatCode="#,##0" sourceLinked="0"/>'
        )
        value_axis.find("c:majorTickMark", ns).addprevious(number_format)

    if colors:
        _paint_series(root, chart_type, len(categories), colors)

    # One series needs no legend (the title names it); a pie always does,
    # since the slices are identified by category. The line template brings one of its own.
    for existing in chart.findall("c:legend", ns):
        chart.remove(existing)
    if len(series) > 1 or chart_type == "pie":
        legend = etree.fromstring(
            f'<c:legend xmlns:c="{_C}"><c:legendPos val="b"/><c:overlay val="0"/></c:legend>'
        )
        chart.find("c:plotArea", ns).addnext(legend)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True), (
        chart_data.xlsx_blob
    )


def add_chart_paragraph(
    document: Any,
    chart_type: str,
    categories: list[str],
    series: dict[str, list[float]],
    title: str,
    width_emu: int,
    height_emu: int,
    fonts: tuple[str, str] | None = None,
    colors: Sequence[str] = (),
) -> Any:
    """Append a paragraph holding a native chart; return the paragraph
    (python-docx `Paragraph`) so the caller can move it. `fonts` is the Latin and East Asian
    typeface of the document's text; `colors` (RRGGBB) paint the series in order, else the
    theme's colours do."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part

    package = document.part.package
    existing = {str(part.partname) for part in package.iter_parts()}
    number = 1
    while f"/word/charts/chart{number}.xml" in existing:
        number += 1

    xml_blob, workbook_blob = _chart_xml(chart_type, categories, series, title, fonts, colors)
    workbook_part = Part(
        PackURI(f"/word/embeddings/Microsoft_Excel_Sheet{number}.xlsx"),
        _XLSX_CT,
        workbook_blob,
        package,
    )
    chart_part = Part(PackURI(f"/word/charts/chart{number}.xml"), _CHART_CT, b"", package)
    workbook_rid = chart_part.relate_to(workbook_part, RT.PACKAGE)
    root = etree.fromstring(xml_blob)
    external = etree.SubElement(root, f"{{{_C}}}externalData", nsmap={"r": _R})
    external.set(f"{{{_R}}}id", workbook_rid)
    etree.SubElement(external, f"{{{_C}}}autoUpdate").set("val", "0")
    chart_part._blob = etree.tostring(  # noqa: SLF001 - generic Part has no setter
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    rid = document.part.relate_to(chart_part, RT.CHART)
    paragraph = document.add_paragraph()
    drawing_id = _next_drawing_id(document)
    inline = (
        f'<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:drawing><wp:inline xmlns:wp="{_WP}" distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{width_emu}" cy="{height_emu}"/>'
        f'<wp:docPr id="{drawing_id}" name="Chart {number}"/>'
        f'<a:graphic xmlns:a="{_A}"><a:graphicData uri="{_C}">'
        f'<c:chart xmlns:c="{_C}" xmlns:r="{_R}" r:id="{rid}"/>'
        f"</a:graphicData></a:graphic></wp:inline></w:drawing></w:r>"
    )
    paragraph._p.append(etree.fromstring(inline))  # noqa: SLF001
    return paragraph


def _next_drawing_id(document: Any) -> int:
    ids = [int(value) for value in document.element.xpath("//wp:docPr/@id") if str(value).isdigit()]
    return max(ids, default=0) + 1
