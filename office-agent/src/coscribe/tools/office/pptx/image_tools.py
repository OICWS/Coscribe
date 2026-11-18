"""Toolkit methods for images, icons, backgrounds, scrims and shape effects."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_ooxml_valid
from ..._thumbnail import render_thumbnail
from . import toolkit_helpers as th
from .effects import SHAPE_EFFECT_TYPES, apply_shape_effect
from .theme import (
    THEME_HEX_RE,
)
from .toolkit_base import ToolkitBase

if TYPE_CHECKING:
    pass


class ImageToolsMixin(ToolkitBase):
    @locked_by_path
    def replace_pptx_image(
        self, path: str, slide: int, shape_index: int | str, image_path: str
    ) -> dict[str, object]:
        """Swap an existing picture's image in place, on any already-
        existing .pptx -- position, size, and crop are all untouched
        because the picture shape itself never changes, only which image
        its `<a:blip>` points at (`Picture.image` has no setter in
        python-pptx; this is the verified real mechanism, see
        PPTX_DESIGN.md §4.2). Call `list_pptx_shapes` first to find the
        picture's `shape_index` (`is_picture: true`). Raster images only
        (PNG/JPEG/GIF/BMP/TIFF -- same formats
        `add_pptx_image` supports); not SVG."""
        image_file = self._check_readable(image_path)
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_picture_shape(target_slide, slide, shape_index)
        _image_part, r_id = shape.part.get_or_add_image_part(str(image_file))
        shape._element.blipFill.blip.rEmbed = r_id  # noqa: SLF001
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def crop_pptx_image(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
    ) -> dict[str, object]:
        """Crop an existing picture shape in place -- each `crop_*` is a
        fraction (0.0-1.0) of the image's own original width/height to
        trim from that edge; the shape's on-slide position/size are
        untouched, only which part of the image shows through inside
        that same box changes (`Picture.crop_*`, the exact mechanism
        `set_pptx_background_image` already uses for its own cover-crop
        -- native python-pptx API, no hand-built XML). Call
        `list_pptx_shapes` first to find the picture's `shape_index`
        (`is_picture: true`). Sets all four values together every call
        (not incremental) -- pass only the edges you actually want
        trimmed, the rest default to 0.0 (uncropped)."""
        if not (0.0 <= crop_left < 1.0 and 0.0 <= crop_right < 1.0):
            raise ValueError("crop_left/crop_right must each be within [0.0, 1.0).")
        if not (0.0 <= crop_top < 1.0 and 0.0 <= crop_bottom < 1.0):
            raise ValueError("crop_top/crop_bottom must each be within [0.0, 1.0).")
        if crop_left + crop_right >= 1.0:
            raise ValueError(
                f"crop_left ({crop_left}) + crop_right ({crop_right}) must be < 1.0 "
                f"-- otherwise no part of the image's width would remain visible."
            )
        if crop_top + crop_bottom >= 1.0:
            raise ValueError(
                f"crop_top ({crop_top}) + crop_bottom ({crop_bottom}) must be < 1.0 "
                f"-- otherwise no part of the image's height would remain visible."
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_picture_shape(target_slide, slide, shape_index)
        shape.crop_left = crop_left
        shape.crop_right = crop_right
        shape.crop_top = crop_top
        shape.crop_bottom = crop_bottom
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "crop_left": crop_left,
            "crop_right": crop_right,
            "crop_top": crop_top,
            "crop_bottom": crop_bottom,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    def list_pptx_icons(self) -> list[str]:
        """Every icon name `add_pptx_icon` accepts, sorted -- a curated
        subset of Lucide (https://lucide.dev, ISC license), not the
        full ~1500-icon set. No path/slide argument: this is a static
        list, the same regardless of which file or slide you're
        working on."""
        return sorted(th.ICON_NAMES)

    @locked_by_path
    def add_pptx_icon(
        self,
        path: str,
        slide: int,
        icon_name: str,
        left_in: float = 1.0,
        top_in: float = 1.0,
        size_in: float = 1.0,
        color: str = "1F2937",
    ) -> dict[str, object]:
        """Insert a real icon (rasterized from Lucide, see
        `list_pptx_icons`) onto an existing slide, as a new square
        picture -- unlike `layout: icon-list`'s glyph-in-a-circle
        (write_pptx's own bundled shape, not a real icon), this is an
        actual recognizable pictogram. Call `list_pptx_icons()` first if
        you're not sure `icon_name` is bundled; an unknown name raises
        immediately rather than silently doing nothing."""
        if icon_name not in th.ICON_NAMES:
            raise ValueError(
                f"Unknown icon {icon_name!r} -- call list_pptx_icons() to see the available names."
            )
        if not THEME_HEX_RE.match(color):
            raise ValueError(f"color {color!r} must be a 6-hex-digit color (no '#').")
        prs, file_path, target_slide = self._open_slide(path, slide)

        from pptx.util import Inches

        recolored = th.recolor_icon(th.ICONS_DIR / f"{icon_name}.png", color)
        buffer = BytesIO()
        recolored.save(buffer, format="PNG")
        buffer.seek(0)
        target_slide.shapes.add_picture(
            buffer, Inches(left_in), Inches(top_in), width=Inches(size_in), height=Inches(size_in)
        )
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "icon_name": icon_name,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def recolor_pptx_icon(
        self, path: str, slide: int, shape_index: int | str, color: str
    ) -> dict[str, object]:
        if not THEME_HEX_RE.match(color):
            raise ValueError(f"color {color!r} must be a 6-hex-digit color (no '#').")
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_picture_shape(target_slide, slide, shape_index)

        from PIL import Image

        current_image = Image.open(BytesIO(shape.image.blob))
        recolored = th.recolor_image(current_image, color)
        buffer = BytesIO()
        recolored.save(buffer, format="PNG")
        buffer.seek(0)
        _image_part, r_id = shape.part.get_or_add_image_part(buffer)
        shape._element.blipFill.blip.rEmbed = r_id  # noqa: SLF001
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "color": color.upper(),
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_image(
        self,
        path: str,
        slide: int,
        image_path: str,
        left: float = 1.0,
        top: float = 1.0,
        width: Optional[float] = None,  # noqa: UP045
        height: Optional[float] = None,  # noqa: UP045
    ) -> dict[str, object]:
        from pptx.util import Inches

        image_file = self._check_readable(image_path)
        prs, file_path, target_slide = self._open_slide(path, slide)

        target_slide.shapes.add_picture(
            str(image_file),
            Inches(left),
            Inches(top),
            width=Inches(width) if width is not None else None,
            height=Inches(height) if height is not None else None,
        )
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def set_pptx_background_image(
        self, path: str, slide: int, image_path: str
    ) -> dict[str, object]:
        """python-pptx's slide.background.fill only supports solid()/
        gradient(), no picture fill at all -- so a background image is a
        full-slide `add_picture` at (0, 0) plus two things python-pptx
        does support natively that a naive stretch-to-fill would skip:
        a CSS `background-size: cover`-style crop (via Picture.crop_*,
        computed from the image's own real aspect ratio, not the slide's)
        so the image isn't distorted, and moving the resulting <p:pic>
        element to be the first shape child of the slide's spTree (right
        after the always-present nvGrpSpPr/grpSpPr) so it renders behind
        every existing placeholder/shape -- add_picture appends at the
        end (front-most) by default, confirmed empirically before writing
        this, which is the opposite of what a background needs."""
        from PIL import Image
        from pptx.oxml.ns import qn

        image_file = self._check_readable(image_path)
        prs, file_path, target_slide = self._open_slide(path, slide)

        with Image.open(image_file) as image:
            image_width, image_height = image.size

        slide_width = prs.slide_width
        slide_height = prs.slide_height
        image_ratio = image_width / image_height
        slide_ratio = slide_width / slide_height

        crop_left = crop_right = crop_top = crop_bottom = 0.0
        if image_ratio > slide_ratio:
            # Image is relatively wider than the slide -- crop its sides.
            visible_fraction = slide_ratio / image_ratio
            crop_left = crop_right = (1 - visible_fraction) / 2
        elif image_ratio < slide_ratio:
            # Image is relatively taller than the slide -- crop top/bottom.
            visible_fraction = image_ratio / slide_ratio
            crop_top = crop_bottom = (1 - visible_fraction) / 2

        picture = target_slide.shapes.add_picture(
            str(image_file), 0, 0, width=slide_width, height=slide_height
        )
        picture.crop_left = crop_left
        picture.crop_right = crop_right
        picture.crop_top = crop_top
        picture.crop_bottom = crop_bottom

        sp_tree = target_slide.shapes._spTree
        pic_element = picture._element
        sp_tree.remove(pic_element)
        group_props = sp_tree.find(qn("p:grpSpPr"))
        insert_at = list(sp_tree).index(group_props) + 1 if group_props is not None else 0
        sp_tree.insert(insert_at, pic_element)

        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_scrim(
        self, path: str, slide: int, opacity: float = 0.35, color: str = "000000"
    ) -> dict[str, object]:
        """A full-slide semi-transparent rectangle, layered above any
        background picture but below every other shape -- keeps title/body
        text legible over a busy photo background, the same "scrim" idea a
        real slide-design tool uses. `python-pptx` has no transparency API
        on `FillFormat` at all, so `<a:alpha>` is hand-appended under the
        `<a:srgbClr>` element `fill.solid()` already builds -- verified
        empirically (a real LibreOffice-rendered black rectangle at 35%
        alpha over a white slide came back mid-gray, not solid black, so
        the transparency is genuinely applied, not silently ignored)
        before writing this. Standalone rather than a `set_pptx_background_
        image` parameter, deliberately -- it composes with a review step
        that decides *whether* a slide actually needs it, rather than
        applying it unconditionally to every background image."""
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.oxml.ns import qn
        from pptx.oxml.xmlchemy import OxmlElement

        prs, file_path, target_slide = self._open_slide(path, slide)

        shape = target_slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(color)  # type: ignore[no-untyped-call]
        shape.line.fill.background()
        shape.shadow.inherit = False

        srgb_clr = shape.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
        alpha = OxmlElement("a:alpha")
        alpha.set("val", str(int(opacity * 100000)))
        srgb_clr.append(alpha)

        sp_tree = target_slide.shapes._spTree
        scrim_element = shape._element
        sp_tree.remove(scrim_element)
        existing_pics = sp_tree.findall(qn("p:pic"))
        if existing_pics:
            insert_at = list(sp_tree).index(existing_pics[-1]) + 1
        else:
            group_props = sp_tree.find(qn("p:grpSpPr"))
            insert_at = list(sp_tree).index(group_props) + 1 if group_props is not None else 0
        sp_tree.insert(insert_at, scrim_element)

        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_shape_effect(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        effect: str,
        color: str = "000000",
        opacity: float = 0.4,
        size_pt: float = 8.0,
        distance_pt: float = 4.0,
        direction: float = 45.0,
    ) -> dict[str, object]:
        """Apply a drop shadow, glow, or soft edge to one shape -- any
        kind (autoshape, picture, connector), since CT_EffectList (the
        `<p:spPr>` child that carries these) is shared by all of them.
        python-pptx has no public API for this at all -- its own
        ShadowFormat can only suppress an inherited theme shadow
        (`shape.shadow.inherit = False`, used by add_pptx_scrim above),
        never create or customize one -- so every effect element this
        writes is hand-built against the real ECMA-376 schema
        (`_ooxml_schemas/transitional/dml-main.xsd`'s CT_EffectList/
        CT_GlowEffect/CT_OuterShadowEffect/CT_SoftEdgesEffect).

        Deliberately narrower than the full schema, matching
        set_pptx_transition/add_pptx_animation's own precedent -- only
        the two color-bearing effects real slide design actually reaches
        for (shadow, glow) and one color-free effect (soft_edge) are
        supported; blur/fillOverlay/innerShdw/prstShdw/reflection are
        not."""
        if effect not in SHAPE_EFFECT_TYPES:
            raise ValueError(f"effect {effect!r} must be one of {sorted(SHAPE_EFFECT_TYPES)}.")
        if effect != "none":
            if not THEME_HEX_RE.match(color):
                raise ValueError(f"color {color!r} must be a 6-hex-digit color (no '#').")
            if not 0.0 <= opacity <= 1.0:
                raise ValueError(f"opacity {opacity} must be between 0.0 and 1.0.")
            if size_pt <= 0:
                raise ValueError(f"size_pt {size_pt} must be positive.")
            if effect == "shadow" and distance_pt < 0:
                raise ValueError(f"distance_pt {distance_pt} must be non-negative.")

        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        apply_shape_effect(shape, effect, color.upper(), opacity, size_pt, distance_pt, direction)
        assert_ooxml_valid(target_slide.element, "add_pptx_shape_effect")
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "effect": effect,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }
