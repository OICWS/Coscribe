"""Copying a template's slide parts for `fill_pptx_template` and `duplicate_pptx_slide`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .xmlns import R_NS

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType


def duplicate_slide_part(prs: PresentationType, source_slide: Any) -> str:
    """Deep-copies `source_slide`'s own XML part into a new slide part in
    the same package. Returns the new part's relationship id (from the
    presentation part) -- not yet inserted into `<p:sldIdLst>`, the
    caller positions it there.

    Every relationship the source slide has -- its slideLayout, every
    image/chart/hyperlink -- is re-added to the new part pointing at the
    SAME target part, not a deep copy of the target: valid OOXML (a part
    can be related-to by more than one other part), and safe here
    specifically because nothing in this module ever mutates a shared
    target part in place -- `replace_pptx_image`, the only tool that
    changes what a blip points at, always adds a brand-new image part
    and repoints one shape's own blip, never edits an existing image
    part's bytes in place. Every r:id-bearing attribute in the copied
    XML (`<a:blip r:embed>`, `<a:hlinkClick r:id>`, ...) is remapped
    whenever the newly assigned relationship id differs from the
    source's own -- verified live this isn't guaranteed to match (a
    synthetic forced-offset test confirmed the remap still resolves
    every reference correctly, not just in the common case where the
    ids happen to line up).

    Speaker notes are NOT carried over (`notesSlide` relationships are
    skipped) -- a deliberate v1 scope cut, not an oversight: correctly
    duplicating a notes part needs this same clone-plus-remap machinery
    applied recursively to it, and nothing has asked for duplicated
    notes yet. A chart on a duplicated slide will share its
    chart-plus-embedded-workbook part with the original (charts aren't
    deep-copied either) -- a real caveat for a future chart-data-editing
    tool to revisit, not a concern for anything that exists today."""
    from copy import deepcopy

    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    from pptx.parts.slide import SlidePart

    presentation_part = prs.part
    package = presentation_part.package
    source_part = source_slide.part

    partname = presentation_part._next_slide_partname  # noqa: SLF001
    new_element = deepcopy(source_part._element)  # noqa: SLF001
    new_part = SlidePart(partname, source_part.content_type, package, new_element)

    rid_remap: dict[str, str] = {}
    for old_rid, rel in source_part.rels.items():
        if rel.reltype == RT.NOTES_SLIDE:
            continue
        if rel.is_external:
            new_rid = new_part.relate_to(rel.target_ref, rel.reltype, is_external=True)
        else:
            new_rid = new_part.relate_to(rel.target_part, rel.reltype)
        if new_rid != old_rid:
            rid_remap[old_rid] = new_rid

    if rid_remap:
        for element in new_element.iter():
            for attr_name, attr_value in list(element.attrib.items()):
                if attr_name.startswith(f"{{{R_NS}}}") and attr_value in rid_remap:
                    element.set(attr_name, rid_remap[attr_value])

    return presentation_part.relate_to(new_part, RT.SLIDE)


def adjust_template_content_slides(
    prs: PresentationType, slide_roles: list[str], target_count: int
) -> list[str]:
    """Grows or shrinks a loaded template's "content"-role slides in
    place to reach `target_count` slides total -- duplicating or
    deleting only "content"-role slides, never "title"/"closing" -- so
    fill_pptx_template's slide count adapts to however many chunks the
    caller actually gave it, instead of the previous hard requirement
    that the chunk count exactly equal the template's fixed slide count.
    Returns the adjusted role list (same length/order as `prs.slides`
    after this call).

    Reuses the exact same `<p:sldIdLst>`/`duplicate_slide_part`
    machinery `delete_pptx_slide`/`duplicate_pptx_slide` already use and
    this session already verified live (forced-rId-offset test, etc.) --
    this is the same operation, just applied from inside
    fill_pptx_template instead of as a standalone tool call. Growing
    duplicates the *last* content slide repeatedly (each duplicate is an
    identical clone of the same design, so which specific content slide
    is duplicated from doesn't affect the result); shrinking removes
    trailing content slides, keeping the earlier one(s)."""
    from pptx.oxml.ns import qn

    content_positions = [i for i, role in enumerate(slide_roles) if role == "content"]
    n_fixed = len(slide_roles) - len(content_positions)
    n_content_needed = target_count - n_fixed
    if n_content_needed < 0 or (n_content_needed > 0 and not content_positions):
        if content_positions:
            detail = f"{n_fixed} fixed slide(s) plus at least one content slide"
            min_valid = n_fixed + 1
        else:
            detail = f"{n_fixed} fixed slide(s), no repeatable content slide"
            min_valid = n_fixed
        raise ValueError(
            f"this template needs at least {min_valid} chunk(s) total "
            f"({detail}) -- got {target_count}."
        )
    n_content_current = len(content_positions)
    sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001

    if n_content_needed > n_content_current:
        insert_at = content_positions[-1] + 1 if content_positions else 0
        last_index = content_positions[-1] if content_positions else -1
        for _ in range(n_content_needed - n_content_current):
            source_slide = prs.slides[last_index]
            new_rid = duplicate_slide_part(prs, source_slide)
            new_sld_id = sld_id_lst.add_sldId(new_rid)
            sld_id_lst.remove(new_sld_id)
            last_index += 1
            sld_id_lst.insert(last_index, new_sld_id)
        return (
            slide_roles[:insert_at]
            + ["content"] * (n_content_needed - n_content_current)
            + slide_roles[insert_at:]
        )

    if n_content_needed < n_content_current:
        to_remove = set(content_positions[n_content_needed:])
        sld_id_elements = list(sld_id_lst)
        for index in sorted(to_remove, reverse=True):
            r_id = sld_id_elements[index].get(qn("r:id"))
            prs.part.drop_rel(r_id)
            sld_id_lst.remove(sld_id_elements[index])
        return [role for i, role in enumerate(slide_roles) if i not in to_remove]

    return slide_roles
