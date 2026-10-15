"""SmartArt in an uploaded deck: detecting it and reaching its data part. python-pptx neither
detects nor reads SmartArt, and nothing outside PowerPoint can generate it."""

from __future__ import annotations

from typing import Any

# SmartArt: python-pptx has no first-class detection or reading for it at
# all -- `GraphicFrame.shape_type` simply returns None for this case (its
# own docstring says so explicitly: "This value is None when none of
# these four types apply, for example when the shape contains
# SmartArt"). There's also no way to *generate* real SmartArt from
# outside PowerPoint -- the layout algorithm lives in the client itself,
# not the file format (confirmed: Apache POI, a mature OOXML library,
# only ever *reads* SmartArt via a `@Beta`-flagged best-effort class,
# never writes it). What's buildable and genuinely useful instead:
# detecting that an *uploaded* file's shape is SmartArt and extracting
# its nodes' own text, so the model can see what a diagram actually said
# before deciding how to rebuild the slide with the deck tools.
#
# The graphicData uri and <dgm:relIds>'s `dm` relationship-id below are
# cross-checked against Apache POI's real, working
# `XSLFDiagram.DRAWINGML_DIAGRAM_URI` constant and its
# `relIds.getDm()`-based data-model-part resolution -- not guessed. The
# <dgm:pt>/<dgm:t> text-body structure is cross-checked against
# LibreOffice's real oox filter source (`PtContext::onCreateContext`
# routes `DGM_TOKEN(t)` to the exact same `TextBodyContext` class used
# for every other DrawingML text body, and doesn't filter by a point's
# own `type` attribute when deciding whether to parse its text) -- both
# real, independent, working OOXML-consuming implementations, not just
# the written spec.
SMARTART_NS = "http://schemas.openxmlformats.org/drawingml/2006/diagram"


def is_smartart(shape: Any) -> bool:
    """True if `shape` is a <p:graphicFrame> containing real SmartArt."""
    from pptx.shapes.graphfrm import GraphicFrame

    if not isinstance(shape, GraphicFrame):
        return False
    graphic_data_uri: str | None = shape._graphicFrame.graphicData_uri  # noqa: SLF001
    return graphic_data_uri == SMARTART_NS


def smartart_text(shape: Any) -> list[str]:
    """Every SmartArt node's own text, one entry per <dgm:pt> that has
    non-empty text (skipping structural/transition points, which in
    practice never carry a <dgm:t> child at all -- see this section's
    own comment on LibreOffice's real parser). Returns [] if `shape`
    isn't SmartArt or its data-model part can't be resolved (should not
    happen for a real, schema-valid file, but this is a best-effort
    read, not a requirement)."""
    from pptx.oxml.ns import qn

    if not is_smartart(shape):
        return []
    graphic_data = shape._graphicFrame.graphic.graphicData  # noqa: SLF001
    rel_ids = graphic_data.find(f"{{{SMARTART_NS}}}relIds")
    if rel_ids is None:
        return []
    dm_rId = rel_ids.get(qn("r:dm"))
    if dm_rId is None:
        return []
    try:
        data_part = shape.part.related_part(dm_rId)
    except KeyError:
        return []

    from lxml import etree

    root = etree.fromstring(data_part.blob)
    texts: list[str] = []
    for pt in root.iter(f"{{{SMARTART_NS}}}pt"):
        t_element = pt.find(f"{{{SMARTART_NS}}}t")
        if t_element is None:
            continue
        # Runs within one paragraph concatenate directly (no separator,
        # same as python-pptx's own text_frame.text within a paragraph);
        # separate paragraphs within one point get a space between them.
        paragraphs = [
            "".join(run.text or "" for run in paragraph.iter(qn("a:t")))
            for paragraph in t_element.iter(qn("a:p"))
        ]
        joined = " ".join(p for p in paragraphs if p).strip()
        if joined:
            texts.append(joined)
    return texts


def smartart_data_part(shape: Any) -> Any:
    """The related package part holding a SmartArt shape's real, editable
    text/structure (`ppt/diagrams/dataN.xml`) -- a SmartArt shape's own
    inline `<p:graphicFrame>` XML in the slide is just relationship
    pointers to this and three sibling parts (layout/quickStyle/colors),
    see `smartart_text`'s own identical lookup above. Raises rather than
    returning `None` -- every call site here is already inside a
    `part in ("auto", "smartart_data")` branch that only runs for a shape
    `is_smartart` already confirmed, so a lookup failure past that point
    means a malformed file, a real error worth surfacing, not a routine
    "not SmartArt" case (`smartart_text`'s own `[]`-on-failure is a
    best-effort *read*; this backs a tool call that should say clearly
    why it can't proceed)."""
    from pptx.oxml.ns import qn

    if not is_smartart(shape):
        raise ValueError("This shape isn't SmartArt -- it has no separate data part to target.")
    graphic_data = shape._graphicFrame.graphic.graphicData  # noqa: SLF001
    rel_ids = graphic_data.find(f"{{{SMARTART_NS}}}relIds")
    if rel_ids is None:
        raise ValueError("This SmartArt shape has no relIds -- its data part can't be resolved.")
    dm_rId = rel_ids.get(qn("r:dm"))
    if dm_rId is None:
        raise ValueError(
            "This SmartArt shape has no r:dm relationship -- its data part can't be resolved."
        )
    try:
        return shape.part.related_part(dm_rId)
    except KeyError as exc:
        raise ValueError(
            f"This SmartArt shape's data part ({dm_rId}) is missing from the file."
        ) from exc
