"""DrawingML shape effects (shadow, glow, soft edge) written into a shape's `<a:effectLst>`."""

from __future__ import annotations

from typing import Any

# DrawingML shape effects (drop shadow / glow / soft edge) -- CT_EffectList,
# a <p:spPr> child shared by every shape kind (autoshape/picture/connector),
# real schema in _ooxml_schemas/transitional/dml-main.xsd. python-pptx has
# zero public API for this (its own ShadowFormat can only *suppress* an
# *inherited* theme shadow -- shape.shadow.inherit = False, used by
# add_pptx_scrim -- never create/customize one), so every effect
# element below is hand-built. CT_EffectList's real child order is fixed
# (blur, fillOverlay, glow, innerShdw, outerShdw, prstShdw, reflection,
# softEdge), each optional and maxOccurs=1 -- apply_shape_effect below
# always inserts a new effect at the correct position relative to whichever
# other supported effects (if any) are already present, rather than
# assuming effectLst is either empty or already holds only this tool's own
# children. Verified live in a REPL: python-pptx's own oxml class for
# <p:spPr> (pptx.oxml.shapes.shared.CT_ShapeProperties) already declares
# effectLst = ZeroOrOne("a:effectLst", successors=...), so
# spPr.get_or_add_effectLst() alone (no hand-XML needed) already inserts
# <a:effectLst> at the schema-correct position within <p:spPr> -- confirmed
# for both autoshapes and pictures.
_EFFECT_LIST_CHILD_LOCALNAMES = (
    "blur",
    "fillOverlay",
    "glow",
    "innerShdw",
    "outerShdw",
    "prstShdw",
    "reflection",
    "softEdge",
)
_SHAPE_EFFECT_LOCALNAMES = {"glow": "glow", "shadow": "outerShdw", "soft_edge": "softEdge"}
SHAPE_EFFECT_TYPES = frozenset({"shadow", "glow", "soft_edge", "none"})


def _shape_effect_color_element(color: str, opacity: float) -> Any:
    """<a:srgbClr val="RRGGBB"><a:alpha val="NNNNN"/></a:srgbClr> -- the same
    EG_ColorChoice pattern add_pptx_scrim already hand-builds for its own
    <a:solidFill>, reused here for <a:glow>/<a:outerShdw>."""
    from pptx.oxml.xmlchemy import OxmlElement

    srgb_clr = OxmlElement("a:srgbClr")
    srgb_clr.set("val", color)
    alpha = OxmlElement("a:alpha")
    alpha.set("val", str(round(opacity * 100000)))
    srgb_clr.append(alpha)
    return srgb_clr


def _build_shape_effect_element(
    effect: str, color: str, opacity: float, size_pt: float, distance_pt: float, direction: float
) -> Any:
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Pt

    if effect == "glow":
        glow = OxmlElement("a:glow")
        glow.set("rad", str(Pt(size_pt)))
        glow.append(_shape_effect_color_element(color, opacity))
        return glow
    if effect == "soft_edge":
        soft_edge = OxmlElement("a:softEdge")
        soft_edge.set("rad", str(Pt(size_pt)))
        return soft_edge
    # "shadow" -- CT_OuterShadowEffect. dir is in 60,000ths of a degree,
    # clockwise from 3 o'clock -- the same OOXML angle convention shape
    # rotation (xfrm@rot) and every other DrawingML angle attribute use.
    outer_shdw = OxmlElement("a:outerShdw")
    outer_shdw.set("blurRad", str(Pt(size_pt)))
    outer_shdw.set("dist", str(Pt(distance_pt)))
    outer_shdw.set("dir", str(round(direction * 60000) % 21600000))
    outer_shdw.set("rotWithShape", "0")
    outer_shdw.append(_shape_effect_color_element(color, opacity))
    return outer_shdw


def apply_shape_effect(
    shape: Any,
    effect: str,
    color: str,
    opacity: float,
    size_pt: float,
    distance_pt: float,
    direction: float,
) -> None:
    """Inserts (or, for effect="none", removes) one effect element inside
    this shape's <a:effectLst>, at the position CT_EffectList's own fixed
    child order requires relative to whichever other supported effect
    type(s) (if any) are already present. Re-applying the same `effect`
    replaces its own existing element in place (find-and-remove first --
    the schema caps each child tag at one), rather than raising or
    stacking an invalid duplicate; applying a *different* `effect` leaves
    any other effect type already on this shape untouched, so effects
    compose across separate calls (e.g. shadow, then soft_edge, leaves
    both)."""
    from pptx.oxml.ns import qn

    effect_lst = shape._element.spPr.get_or_add_effectLst()  # noqa: SLF001

    if effect == "none":
        for local_name in _SHAPE_EFFECT_LOCALNAMES.values():
            existing = effect_lst.find(qn(f"a:{local_name}"))
            if existing is not None:
                effect_lst.remove(existing)
        return

    target_local = _SHAPE_EFFECT_LOCALNAMES[effect]
    target_rank = _EFFECT_LIST_CHILD_LOCALNAMES.index(target_local)
    existing = effect_lst.find(qn(f"a:{target_local}"))
    if existing is not None:
        effect_lst.remove(existing)

    local_by_tag = {qn(f"a:{name}"): name for name in _EFFECT_LIST_CHILD_LOCALNAMES}
    insert_at = 0
    for child in effect_lst:
        child_local = local_by_tag.get(child.tag)
        if child_local is None or _EFFECT_LIST_CHILD_LOCALNAMES.index(child_local) >= target_rank:
            break
        insert_at += 1

    new_element = _build_shape_effect_element(
        effect, color, opacity, size_pt, distance_pt, direction
    )
    effect_lst.insert(insert_at, new_element)
