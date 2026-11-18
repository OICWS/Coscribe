"""Tool wrappers for images, icons, backgrounds, scrims and shape effects."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from .toolkit import PresentationToolkit


def build_images_tools(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def replace_pptx_image(
        path: str, slide: int, shape_index: str, image_path: str
    ) -> dict[str, object]:
        """Swap an existing picture's image in place on an existing
        PowerPoint (.pptx) file's slide -- position, size, and crop are
        all kept exactly as they were, only the image itself changes.
        The tool for replacing a photo/icon already placed in a real
        uploaded deck (or one coscribe already generated) with a
        different one, without touching its placement.

        Call list_pptx_shapes(path, slide) first to find the picture's
        shape_index (is_picture: true).

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the picture is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            image_path: path to the new image file already on disk,
                relative to the workspace root. Raster formats only
                (PNG/JPEG/GIF/BMP/TIFF, same as add_pptx_image) -- not SVG.
        """
        return toolkit.replace_pptx_image(
            path=path, slide=slide, shape_index=shape_index, image_path=image_path
        )

    def crop_pptx_image(
        path: str,
        slide: int,
        shape_index: str,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
    ) -> dict[str, object]:
        """Crop an existing picture shape on an existing PowerPoint
        (.pptx) file's slide, in place -- the shape's on-slide position/
        size are untouched, only which part of the image shows through
        inside that same box changes.

        Call list_pptx_shapes(path, slide) first to find the picture's
        shape_index (is_picture: true).

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the picture is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            crop_left: fraction (0.0-1.0) of the image's own width to trim
                from its left edge. Defaults to 0.0 (no crop).
            crop_right: fraction (0.0-1.0) of the image's own width to trim
                from its right edge. Defaults to 0.0 (no crop).
            crop_top: fraction (0.0-1.0) of the image's own height to trim
                from its top edge. Defaults to 0.0 (no crop).
            crop_bottom: fraction (0.0-1.0) of the image's own height to
                trim from its bottom edge. Defaults to 0.0 (no crop).
        """
        return toolkit.crop_pptx_image(
            path=path,
            slide=slide,
            shape_index=shape_index,
            crop_left=crop_left,
            crop_right=crop_right,
            crop_top=crop_top,
            crop_bottom=crop_bottom,
        )

    def list_pptx_icons() -> list[str]:
        """List every icon name add_pptx_icon accepts -- a curated
        subset of Lucide (https://lucide.dev, ISC license), not its
        full ~1500-icon set. No arguments: this is a static list, not
        specific to any file."""
        return toolkit.list_pptx_icons()

    def add_pptx_icon(
        path: str,
        slide: int,
        icon_name: str,
        left_in: float = 1.0,
        top_in: float = 1.0,
        size_in: float = 1.0,
        color: str = "1F2937",
    ) -> dict[str, object]:
        """Insert a real icon onto an existing slide in a PowerPoint
        (.pptx) file, as a new square picture -- unlike write_pptx's
        `layout: icon-list` (a glyph inside a plain colored circle),
        this is an actual recognizable pictogram (rasterized from
        Lucide). Use this to add a real icon to a slide you're editing,
        or alongside other shapes on a freshly-built one.

        Call list_pptx_icons() first if you're not sure icon_name is
        bundled -- an unknown name raises immediately.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to add the icon to
            icon_name: one of list_pptx_icons()'s names, e.g. "check",
                "trending-up", "lightbulb"
            left_in: horizontal position in inches from the slide's left edge
            top_in: vertical position in inches from the slide's top edge
            size_in: width and height in inches (icons are square)
            color: 6-hex-digit fill color, no '#' (default a dark
                slate gray, "1F2937")
        """
        return toolkit.add_pptx_icon(
            path=path,
            slide=slide,
            icon_name=icon_name,
            left_in=left_in,
            top_in=top_in,
            size_in=size_in,
            color=color,
        )

    def recolor_pptx_icon(
        path: str, slide: int, shape_index: str, color: str
    ) -> dict[str, object]:
        """Change the color of an icon or logo-like picture already on a
        slide, in place -- position, size, and crop are untouched, only
        the pixels change (same relationship-swap mechanism as
        `replace_pptx_image`).

        Works by re-coloring the shape's own *current* image from its
        existing alpha (transparency) channel, not by re-fetching a
        bundled icon by name -- so it recolors any icon `add_pptx_icon`
        placed (regardless of which one), and will also work on any
        other transparent-background picture with a real silhouette.
        It does **not** detect edges or shapes: every pixel that isn't
        already transparent becomes the new solid color. Using it on an
        opaque photo (no real transparency) will flatten the whole
        picture to one solid color block -- only use this on icons,
        logos, or other transparent-background pictograms.

        Call `list_pptx_shapes` first to find `shape_index`
        (`is_picture: true`).

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number the icon is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            color: new 6-hex-digit fill color, no '#'
        """
        return toolkit.recolor_pptx_icon(
            path=path, slide=slide, shape_index=shape_index, color=color
        )

    def add_pptx_image(
        path: str,
        slide: int,
        image_path: str,
        left: float = 1.0,
        top: float = 1.0,
        width: Optional[float] = None,  # noqa: UP045
        height: Optional[float] = None,  # noqa: UP045
    ) -> dict[str, object]:
        """Add a picture to an existing slide in a PowerPoint (.pptx) file.

        `image_path` must be a readable image file already on disk (e.g. one
        the user attached, or one generated by another tool). Position and
        size are in inches; `width`/`height` default to the image's native
        aspect ratio scaled from whichever one is given, or the image's
        actual size if neither is given (python-pptx's own default).

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number to add the image to
            image_path: image file to insert, relative to the workspace root
            left: distance from the slide's left edge, in inches
            top: distance from the slide's top edge, in inches
            width: image width in inches; omit to keep the native aspect ratio
            height: image height in inches; omit to keep the native aspect ratio
        """
        return toolkit.add_pptx_image(
            path=path,
            slide=slide,
            image_path=image_path,
            left=left,
            top=top,
            width=width,
            height=height,
        )

    def set_pptx_background_image(path: str, slide: int, image_path: str) -> dict[str, object]:
        """Set a full-bleed background image on one slide in a PowerPoint
        (.pptx) file, behind its existing title/content/other shapes.

        The image is cropped (not stretched) to cover the whole slide
        without distortion, the same way CSS `background-size: cover`
        works -- picked automatically from the image's own aspect ratio,
        nothing to configure. Use search_images + download_image first to
        find and fetch a candidate image, or point at one already in the
        workspace. Images sourced via search_images are NOT filtered by
        license -- treat a deck built with one as a draft, and say so if
        the user seems to be about to send or publish it, rather than
        silently treating the image as clear to use externally.

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number to set the background on
            image_path: image file to use, relative to the workspace root
        """
        return toolkit.set_pptx_background_image(path=path, slide=slide, image_path=image_path)

    def add_pptx_scrim(
        path: str, slide: int, opacity: float = 0.35, color: str = "000000"
    ) -> dict[str, object]:
        """Add a full-slide semi-transparent color layer to one slide in a
        PowerPoint (.pptx) file, between its background image (if any) and
        its other shapes -- keeps title/body text legible over a busy
        photo background instead of leaving it low-contrast.

        Not applied automatically by set_pptx_background_image -- add it
        only when text actually needs it (e.g. review_work flags a
        legibility problem after you set a background image), not as a
        blanket default on every background -- an unnecessary scrim reads
        as decorative filler the same way an unnecessary accent bar does.

        Pick `color` to contrast with the slide's actual text color, not
        its own default of black -- a dark scrim under dark title text
        barely helps (verified: still low-contrast against a busy photo);
        a light scrim (e.g. "FFFFFF") under dark text washes the photo out
        enough to read clearly while staying recognizable.

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number to add the scrim to
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque); 0.35 is
                a reasonable starting point for dark text/light overlay or
                vice versa
            color: hex RGB color, no leading "#", e.g. "000000" for a dark
                scrim (light text over it) or "FFFFFF" for a light scrim
                (dark text over it)
        """
        return toolkit.add_pptx_scrim(path=path, slide=slide, opacity=opacity, color=color)

    def add_pptx_shape_effect(
        path: str,
        slide: int,
        shape_index: str,
        effect: str,
        color: str = "000000",
        opacity: float = 0.4,
        size_pt: float = 8.0,
        distance_pt: float = 4.0,
        direction: float = 45.0,
    ) -> dict[str, object]:
        """Apply a drop shadow, glow, or soft edge to one shape (any kind --
        autoshape, picture, connector) on a slide in a PowerPoint (.pptx)
        file.

        Calling this again with a *different* `effect` on the same shape
        adds that effect alongside whatever it already has (e.g. shadow,
        then soft_edge, leaves both). Calling it again with the *same*
        `effect` replaces that effect's own settings in place.
        `effect="none"` removes every effect this tool manages from the
        shape (color/opacity/size_pt/distance_pt/direction are ignored in
        that case).

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: which shape on that slide -- call list_pptx_shapes
                first to find it
            effect: "shadow", "glow", "soft_edge", or "none" to clear
            color: hex RGB color, no leading "#" -- shadow/glow only,
                ignored for soft_edge/none
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque) --
                shadow/glow only
            size_pt: blur radius in points (shadow), glow radius (glow), or
                softening radius (soft_edge)
            distance_pt: how far the shadow is offset from the shape --
                shadow only, ignored otherwise
            direction: shadow offset direction in degrees, 0 = right,
                90 = down, increasing clockwise (PowerPoint's own angle
                convention) -- shadow only, ignored otherwise
        """
        return toolkit.add_pptx_shape_effect(
            path=path,
            slide=slide,
            shape_index=shape_index,
            effect=effect,
            color=color,
            opacity=opacity,
            size_pt=size_pt,
            distance_pt=distance_pt,
            direction=direction,
        )

    return {
        "replace_pptx_image": replace_pptx_image,
        "crop_pptx_image": crop_pptx_image,
        "list_pptx_icons": list_pptx_icons,
        "add_pptx_icon": add_pptx_icon,
        "recolor_pptx_icon": recolor_pptx_icon,
        "add_pptx_image": add_pptx_image,
        "set_pptx_background_image": set_pptx_background_image,
        "add_pptx_scrim": add_pptx_scrim,
        "add_pptx_shape_effect": add_pptx_shape_effect,
    }
