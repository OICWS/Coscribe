"""Hand-built .pptx inputs shared by the tool tests and the golden tests.

No library can create SmartArt (the layout algorithm lives in PowerPoint, not in the file
format), so the one fixture here writes the package parts directly into a deck python-pptx
saved. Its structure follows what Apache POI's XSLFDiagram and LibreOffice's oox diagram
filter read, and each part validates against ECMA-376 `dml-diagram.xsd` (a data model with
connections, a layout, a style and a colour definition), so a tool that starts validating
diagram parts does not fail on the fixture itself.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from pptx import Presentation

_DGM = "http://schemas.openxmlformats.org/drawingml/2006/diagram"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

_NODES = (
    ("1", "<a:r><a:t>Plan</a:t></a:r>"),
    ("2", "<a:r><a:t>Build</a:t></a:r><a:r><a:t> phase</a:t></a:r>"),
    ("3", "<a:r><a:t>Ship</a:t></a:r>"),
)


def _data_model() -> str:
    points = [
        '<dgm:pt modelId="0" type="doc"><dgm:prSet/><dgm:spPr/><dgm:t><a:bodyPr/><a:lstStyle/>'
        '<a:p><a:endParaRPr lang="en-US"/></a:p></dgm:t></dgm:pt>'
    ]
    connections = []
    for index, (node_id, runs) in enumerate(_NODES):
        parent_transition, sibling_transition, connection = (
            f"1{node_id}",
            f"2{node_id}",
            f"3{node_id}",
        )
        points.append(
            f'<dgm:pt modelId="{node_id}"><dgm:prSet/><dgm:spPr/>'
            f"<dgm:t><a:bodyPr/><a:lstStyle/><a:p>{runs}</a:p></dgm:t></dgm:pt>"
        )
        for transition, kind in ((parent_transition, "parTrans"), (sibling_transition, "sibTrans")):
            points.append(
                f'<dgm:pt modelId="{transition}" type="{kind}" cxnId="{connection}">'
                "<dgm:prSet/><dgm:spPr/></dgm:pt>"
            )
        connections.append(
            f'<dgm:cxn modelId="{connection}" srcId="0" destId="{node_id}" srcOrd="{index}" '
            f'destOrd="0" parTransId="{parent_transition}" sibTransId="{sibling_transition}"/>'
        )
    return (
        f'{_XML}<dgm:dataModel xmlns:dgm="{_DGM}" xmlns:a="{_A}"><dgm:ptLst>{"".join(points)}'
        f"</dgm:ptLst><dgm:cxnLst>{''.join(connections)}</dgm:cxnLst><dgm:bg/><dgm:whole/>"
        "</dgm:dataModel>"
    )


_LAYOUT = (
    f'{_XML}<dgm:layoutDef xmlns:dgm="{_DGM}" '
    'uniqueId="urn:microsoft.com/office/officeart/2005/8/layout/default">'
    '<dgm:title val=""/><dgm:desc val=""/><dgm:catLst/>'
    '<dgm:layoutNode name="diagram"><dgm:alg type="lin"/><dgm:shape/><dgm:presOf/>'
    "</dgm:layoutNode></dgm:layoutDef>"
)
_QUICK_STYLE = (
    f'{_XML}<dgm:styleDef xmlns:dgm="{_DGM}" xmlns:a="{_A}" '
    'uniqueId="urn:microsoft.com/office/officeart/2005/8/quickstyle/simple1">'
    '<dgm:title val=""/><dgm:desc val=""/><dgm:catLst/>'
    '<dgm:scene3d><a:camera prst="orthographicFront"/><a:lightRig rig="threePt" dir="t"/>'
    '</dgm:scene3d><dgm:styleLbl name="node0"><dgm:scene3d><a:camera prst="orthographicFront"/>'
    '<a:lightRig rig="threePt" dir="t"/></dgm:scene3d><dgm:sp3d/><dgm:txPr/><dgm:style>'
    '<a:lnRef idx="2"><a:scrgbClr r="0" g="0" b="0"/></a:lnRef>'
    '<a:fillRef idx="1"><a:scrgbClr r="0" g="0" b="0"/></a:fillRef>'
    '<a:effectRef idx="0"><a:scrgbClr r="0" g="0" b="0"/></a:effectRef>'
    '<a:fontRef idx="minor"><a:schemeClr val="lt1"/></a:fontRef></dgm:style>'
    "</dgm:styleLbl></dgm:styleDef>"
)
_COLORS = (
    f'{_XML}<dgm:colorsDef xmlns:dgm="{_DGM}" xmlns:a="{_A}" '
    'uniqueId="urn:microsoft.com/office/officeart/2005/8/colors/accent1_2">'
    '<dgm:title val=""/><dgm:desc val=""/><dgm:catLst/>'
    '<dgm:styleLbl name="node0"><dgm:fillClrLst meth="repeat"><a:schemeClr val="accent1"/>'
    '</dgm:fillClrLst><dgm:linClrLst meth="repeat"><a:schemeClr val="lt1"/></dgm:linClrLst>'
    "<dgm:effectClrLst/><dgm:txLinClrLst/><dgm:txFillClrLst/><dgm:txEffectClrLst/>"
    "</dgm:styleLbl></dgm:colorsDef>"
)
_GRAPHIC_FRAME = f"""<p:graphicFrame
      xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
      xmlns:a="{_A}" xmlns:r="{_R}">
  <p:nvGraphicFramePr>
    <p:cNvPr id="99" name="SmartArt 1"/>
    <p:cNvGraphicFramePr/>
    <p:nvPr/>
  </p:nvGraphicFramePr>
  <p:xfrm><a:off x="914400" y="914400"/><a:ext cx="4572000" cy="2743200"/></p:xfrm>
  <a:graphic>
    <a:graphicData uri="{_DGM}">
      <dgm:relIds xmlns:dgm="{_DGM}" r:dm="rIdDM1" r:lo="rIdLO1" r:qs="rIdQS1" r:cs="rIdCS1"/>
    </a:graphicData>
  </a:graphic>
</p:graphicFrame>"""

# (part name, relationship type suffix, content type suffix, xml)
_PARTS = (
    ("data1.xml", "diagramData", "diagramData", None),
    ("layout1.xml", "diagramLayout", "diagramLayout", _LAYOUT),
    ("quickStyle1.xml", "diagramQuickStyle", "diagramStyle", _QUICK_STYLE),
    ("colors1.xml", "diagramColors", "diagramColors", _COLORS),
)
_REL_IDS = {
    "data1.xml": "rIdDM1",
    "layout1.xml": "rIdLO1",
    "quickStyle1.xml": "rIdQS1",
    "colors1.xml": "rIdCS1",
}


def write_smartart_fixture(path: Path) -> None:
    """Save a one-slide deck at `path` with a SmartArt frame whose nodes read
    "Plan", "Build phase" and "Ship"."""
    base_path = path.with_suffix(".base.pptx")
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6])
    prs.save(str(base_path))

    with zipfile.ZipFile(base_path, "r") as zin:
        contents = {name: zin.read(name) for name in zin.namelist()}

    slide_xml = contents["ppt/slides/slide1.xml"].decode("utf-8")
    contents["ppt/slides/slide1.xml"] = slide_xml.replace(
        "</p:spTree>", _GRAPHIC_FRAME + "</p:spTree>"
    ).encode("utf-8")

    relationships = ""
    overrides = ""
    for name, rel_suffix, content_suffix, xml in _PARTS:
        contents[f"ppt/diagrams/{name}"] = (xml or _data_model()).encode("utf-8")
        relationships += (
            f'<Relationship Id="{_REL_IDS[name]}" Type="{_R}/{rel_suffix}" '
            f'Target="../diagrams/{name}"/>'
        )
        overrides += (
            f'<Override PartName="/ppt/diagrams/{name}" ContentType='
            f'"application/vnd.openxmlformats-officedocument.drawingml.{content_suffix}+xml"/>'
        )
    rels_name = "ppt/slides/_rels/slide1.xml.rels"
    contents[rels_name] = (
        contents[rels_name]
        .decode("utf-8")
        .replace("</Relationships>", relationships + "</Relationships>")
    ).encode("utf-8")
    contents["[Content_Types].xml"] = (
        contents["[Content_Types].xml"].decode("utf-8").replace("</Types>", overrides + "</Types>")
    ).encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in contents.items():
            zout.writestr(name, data)
    base_path.unlink()
