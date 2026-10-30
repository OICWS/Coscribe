"""Toolkit methods for raw XML, notes, transitions, animations and audio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_ooxml_valid
from ..._pptx_shapes import in_group
from . import toolkit_helpers as th
from .animation import (
    ANIMATIONS,
    AUDIO_CONTENT_TYPES,
    AUDIO_MARKER_SIZE_EMU,
    AUDIO_TRIGGERS,
    TRIGGERS,
    add_animation_step,
    build_audio_pic_element,
    build_audio_timing_node,
    ensure_paragraph_build,
    next_timing_id,
    register_audio_media_part_class,
    resolve_animation_preset,
    timing_root_child_list,
    verify_animation_readback,
)
from .smartart import is_smartart, smartart_data_part
from .toolkit_base import ToolkitBase
from .transitions import (
    TRANSITIONS,
    set_slide_transition,
)
from .xmlns import (
    P_NS,
)

if TYPE_CHECKING:
    pass


class XmlAnimationMixin(ToolkitBase):
    def list_pptx_transition_types(self) -> list[str]:
        """Every `transition` name `set_pptx_transition` accepts, sorted --
        PowerPoint's real native transition gallery (48 effects) plus 8
        legacy aliases. No path/slide argument: this is a static list, the
        same regardless of which file or slide you're working on."""
        return sorted(TRANSITIONS - {"none"})

    def list_pptx_animation_types(self) -> list[str]:
        """Every `animation` name `add_pptx_animation` accepts, sorted --
        PowerPoint's real native animation gallery (203 presets, grouped
        by the `entrance_`/`emphasis_`/`exit_`/`path_` prefix) plus the 6
        legacy short aliases. No path/slide argument: this is a static
        list, the same regardless of which file or slide you're working
        on."""
        return sorted(ANIMATIONS)

    @locked_by_path
    def read_pptx_xml(
        self, path: str, slide: int, shape_index: int | str, part: str = "auto"
    ) -> dict[str, object]:
        """Raw OOXML for one shape -- the escape hatch for anything
        python-pptx has no API for at all beyond what add_pptx_shape_effect/
        add_pptx_animation/set_pptx_transition already hand-write (see this
        file's own module docstring): editing SmartArt node text, or
        inspecting/tweaking any other element this package's own tools
        don't wrap. Always read before calling edit_pptx_xml -- the real
        element names/namespaces/nesting are what xpath there has to
        target, and this is the only way to see them."""
        from lxml import etree

        th.validate_xml_part_arg(part)
        _prs, _file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        use_smartart_data = part == "smartart_data" or (part == "auto" and is_smartart(shape))
        if use_smartart_data:
            root = etree.fromstring(smartart_data_part(shape).blob)
            source = "smartart_data"
        else:
            root = shape._element  # noqa: SLF001
            source = "shape"
        return {
            "xml": etree.tostring(root, pretty_print=True, encoding="unicode"),
            "source": source,
        }

    @locked_by_path
    def edit_pptx_xml(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        xpath: str,
        new_text: Optional[str] = None,  # noqa: UP045
        set_attributes: Optional[str] = None,  # noqa: UP045
        part: str = "auto",
    ) -> dict[str, object]:
        """Edit one element inside a shape's raw OOXML, found by XPath --
        the narrow, bounded escape hatch ROADMAP.md's own "Later" backlog
        named: element-scoped (an xpath must resolve to exactly one real
        element, same "unique match or raise" discipline edit_file's own
        old_text uses), not an unrestricted whole-file patch -- there's no
        way to add/remove/reorder elements here, only change an existing
        one's text or attributes. Reach for this only when no dedicated
        tool already covers what's needed; it's real hand-XML, no
        argument-level guardrails beyond "the result must still be
        well-formed"."""
        from lxml import etree

        if new_text is None and not set_attributes:
            raise ValueError("Provide new_text and/or set_attributes -- nothing to change.")
        th.validate_xml_part_arg(part)
        parsed_attributes = th.parse_set_attributes(set_attributes)

        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        use_smartart_data = part == "smartart_data" or (part == "auto" and is_smartart(shape))

        # Real gotcha, verified empirically (not assumed): `//foo` in
        # XPath means "search the whole document this node belongs to",
        # not "search this node's own descendants" -- calling
        # `.xpath("//dgm:t")` directly on `shape._element` (which lives
        # inside the full <p:sld> tree, alongside every *other* shape on
        # the slide) would silently match content in a sibling shape too,
        # breaking the "exactly one match" contract in a way that could
        # edit the wrong shape without ever raising. Parsing a standalone
        # copy of just this shape's own serialized XML sidesteps the
        # whole problem -- `//` on a detached tree can only ever reach
        # that tree's own content, no cross-shape leakage possible. The
        # SmartArt data part is already parsed this same way below
        # (a fresh `etree.fromstring(data_part.blob)`, its own document),
        # so this makes both sources behave identically.
        data_part = None
        original_shape_element = None
        if use_smartart_data:
            data_part = smartart_data_part(shape)
            root = etree.fromstring(data_part.blob)
            source = "smartart_data"
        else:
            original_shape_element = shape._element  # noqa: SLF001
            root = etree.fromstring(etree.tostring(original_shape_element))
            source = "shape"

        matches = root.xpath(xpath, namespaces=th.GENERIC_XML_NSMAP)
        if len(matches) != 1:
            raise ValueError(
                f"xpath {xpath!r} matched {len(matches)} element(s) inside this {source} "
                "XML -- must match exactly one. Call read_pptx_xml first to see the real "
                "structure and narrow the xpath."
            )
        element = matches[0]
        if not isinstance(element, etree._Element):  # noqa: SLF001
            raise ValueError(
                f"xpath {xpath!r} matched an attribute or text value, not an element -- "
                "target the element itself (e.g. '//dgm:t' not '//dgm:t/@type')."
            )

        if new_text is not None:
            element.text = new_text
        for name, value in parsed_attributes.items():
            element.set(th.resolve_xml_qname(name), value)

        # Splice the edited detached copy back into the real, live slide
        # tree at the shape's own original position (getparent().replace,
        # not append -- this preserves shape order, since a slide's
        # z-order is its shapes' own document order). Then validate the
        # *whole slide* via assert_ooxml_valid, same "never serialize an
        # unvalidated write" guarantee every other hand-XML tool in this
        # file makes (the ECMA-376 Transitional/pml.xsd this file already
        # vendors) -- catches a mistake in this edit even if it's
        # syntactically well-formed (e.g. a required child now missing).
        # A SmartArt data part's own <dgm:dataModel> root has no vendored
        # schema here (a genuinely separate schema this codebase hasn't
        # needed until now) -- well-formedness (the etree.tostring below
        # already guarantees that much, or it would have raised) is the
        # only check available for that source, documented honestly
        # rather than silently claiming a stronger guarantee than this
        # tool actually gives.
        if source == "shape":
            assert original_shape_element is not None  # narrows for mypy
            original_shape_element.getparent().replace(original_shape_element, root)
            assert_ooxml_valid(target_slide.element, "edit_pptx_xml")
        else:
            assert data_part is not None  # narrows for mypy -- true whenever source != "shape"
            data_part.blob = etree.tostring(
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "source": source,
        }

    @locked_by_path
    def set_pptx_notes(self, path: str, slide: int, notes: str) -> dict[str, object]:
        prs, file_path, target_slide = self._open_slide(path, slide)
        target_slide.notes_slide.notes_text_frame.text = notes
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "slide": slide}

    @locked_by_path
    def set_pptx_transition(
        self, path: str, slide: int, transition: str, duration: float = 1.0
    ) -> dict[str, object]:
        if transition not in TRANSITIONS:
            raise ValueError(
                f"Unknown transition {transition!r}. Use one of: {', '.join(sorted(TRANSITIONS))}"
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        set_slide_transition(target_slide.element, transition, duration)
        assert_ooxml_valid(target_slide.element, "set_pptx_transition")
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "slide": slide, "transition": transition}

    @locked_by_path
    def add_pptx_animation(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        animation: str,
        duration: float = 0.5,
        trigger: str = "on-click",
        delay: float = 0.0,
        by_paragraph: bool = False,
    ) -> dict[str, object]:
        if animation not in ANIMATIONS:
            raise ValueError(
                f"Unknown animation {animation!r}. Use one of: {', '.join(sorted(ANIMATIONS))}"
            )
        if trigger not in TRIGGERS:
            raise ValueError(
                f"Unknown trigger {trigger!r}. Use one of: {', '.join(sorted(TRIGGERS))}"
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        if in_group(shape):
            raise ValueError(
                f"Shape {shape_index!r} is inside a group, and PowerPoint animates a group as one "
                "shape: animate the group (the path before the last '/') instead."
            )
        shape_id = shape.shape_id
        duration_ms = max(1, round(duration * 1000))
        delay_ms = max(0, round(delay * 1000))

        paragraph_indexes: list[int] | None = None
        if by_paragraph:
            if not shape.has_text_frame:
                raise ValueError(
                    f"add_pptx_animation: shape {shape_index} on slide {slide} has no text "
                    "frame -- by_paragraph needs a shape with text."
                )
            paragraph_indexes = [
                index
                for index, paragraph in enumerate(shape.text_frame.paragraphs)
                if paragraph.text.strip()
            ]
            if not paragraph_indexes:
                raise ValueError(
                    f"add_pptx_animation: shape {shape_index} on slide {slide} has no "
                    "non-empty paragraphs to animate by_paragraph."
                )
            for paragraph_index in paragraph_indexes:
                add_animation_step(
                    target_slide.element,
                    shape_id,
                    animation,
                    duration_ms,
                    trigger,
                    delay_ms,
                    paragraph_index,
                )
            timing = target_slide.element.find(f"{{{P_NS}}}timing")
            ensure_paragraph_build(timing, shape_id)
        else:
            add_animation_step(
                target_slide.element, shape_id, animation, duration_ms, trigger, delay_ms, None
            )

        assert_ooxml_valid(target_slide.element, "add_pptx_animation")

        # Save to a temp file and verify before touching the real file --
        # if the read-back check fails, the user's file is left untouched
        # rather than silently left in a possibly-broken state.
        tmp_path = file_path.with_name(f"{file_path.name}.animation-tmp")
        prs.save(str(tmp_path))
        try:
            verify_animation_readback(
                tmp_path, slide, shape_id, animation, trigger, paragraph_indexes
            )
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        tmp_path.replace(file_path)

        preset = resolve_animation_preset(animation)
        actual_duration_ms = (
            duration_ms
            if preset["duration_scalable"] and preset["default_duration_ms"] is not None
            else preset["default_duration_ms"]
        )
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "animation": animation,
            "trigger": trigger,
            "by_paragraph": by_paragraph,
            "paragraph_count": len(paragraph_indexes) if paragraph_indexes is not None else None,
            "duration_ms": actual_duration_ms,
        }

    @locked_by_path
    def add_pptx_audio(
        self,
        path: str,
        slide: int,
        audio_path: str,
        left_in: float = 0.3,
        top_in: float = 0.3,
        trigger: str = "auto",
        start_delay: float = 0.0,
        hidden: bool = False,
    ) -> dict[str, object]:
        if trigger not in AUDIO_TRIGGERS:
            raise ValueError(
                f"Unknown trigger {trigger!r}. Use one of: {', '.join(sorted(AUDIO_TRIGGERS))}"
            )
        audio_file = self._check_readable(audio_path)
        ext = audio_file.suffix.lower()
        if ext not in AUDIO_CONTENT_TYPES:
            raise ValueError(
                f"add_pptx_audio: unsupported audio format {ext!r} on {audio_path!r} -- "
                f"use one of: {', '.join(sorted(AUDIO_CONTENT_TYPES))}"
            )
        prs, file_path, target_slide = self._open_slide(path, slide)

        import io

        from lxml import etree
        from pptx.media import SPEAKER_IMAGE_BYTES, Video
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml import parse_xml
        from pptx.util import Inches

        # `Video` is python-pptx's own generic media-blob wrapper (used
        # internally by `add_movie`) -- nothing in it is video-specific,
        # confirmed by reading its source before reusing it here. Its own
        # `get_or_add_media_part`/`relate_to`/`get_or_add_image_part` are
        # the same real relationship-writing plumbing `add_movie` uses,
        # reused directly rather than hand-rolled, EXCEPT for the actual
        # audio relationship type: `add_movie`'s own higher-level
        # `get_or_add_video_media_part` hardcodes `RT.VIDEO` for the
        # legacy relationship, which would be semantically wrong for
        # audio (and mismatched against this method's own `<a:audioFile>`
        # element) -- built directly with the real `RT.AUDIO` type
        # instead, confirmed to exist in python-pptx's own constants.
        register_audio_media_part_class()
        video = Video.from_path_or_file_like(str(audio_file), AUDIO_CONTENT_TYPES[ext])
        slide_part = target_slide.part
        media_part = slide_part.package.get_or_add_media_part(video)
        audio_rid = slide_part.relate_to(media_part, RT.AUDIO)
        media_rid = slide_part.relate_to(media_part, RT.MEDIA)
        # The default "media loudspeaker" icon python-pptx already bundles
        # for `add_movie`'s own poster-frame fallback -- reused as-is
        # rather than vendoring hugohe3/ppt-master's own separate icon,
        # since coscribe already ships python-pptx as a real dependency.
        _, poster_rid = slide_part.get_or_add_image_part(io.BytesIO(SPEAKER_IMAGE_BYTES))

        shape_id = target_slide.shapes._next_shape_id
        shape_name = audio_file.name
        if hidden:
            x_emu = y_emu = -AUDIO_MARKER_SIZE_EMU
        else:
            x_emu, y_emu = int(Inches(left_in)), int(Inches(top_in))

        pic = build_audio_pic_element(
            shape_id,
            shape_name,
            audio_rid,
            media_rid,
            poster_rid,
            x_emu,
            y_emu,
            AUDIO_MARKER_SIZE_EMU,
        )
        # `build_audio_pic_element` returns a plain lxml element -- python-
        # pptx's own shape factory (invoked whenever `target_slide.shapes`
        # is iterated, which `render_pptx_preview`/`list_pptx_shapes` and
        # this method's own shape_index computation below all do) expects
        # its custom `CT_Picture` subclass instead, keyed off a parser
        # python-pptx registers globally -- round-tripping through
        # `parse_xml(etree.tostring(...))` re-parses with that same
        # parser, confirmed empirically to yield the real `CT_Picture`
        # class regardless of the (arbitrary, auto-generated) namespace
        # prefixes `etree.tostring` emits for Clark-notation tags.
        target_slide.shapes._spTree.append(parse_xml(etree.tostring(pic)))
        shape_index = len(list(target_slide.shapes)) - 1

        root_child = timing_root_child_list(target_slide.element)
        timing = target_slide.element.find(f"{{{P_NS}}}timing")
        next_id = next_timing_id(timing)
        start_delay_ms = None if trigger == "on-click" else max(0, round(start_delay * 1000))
        root_child.append(build_audio_timing_node(shape_id, next_id, start_delay_ms))

        assert_ooxml_valid(target_slide.element, "add_pptx_audio")
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "trigger": trigger,
            "start_delay": (None if start_delay_ms is None else round(start_delay_ms / 1000, 3)),
            "hidden": hidden,
        }
