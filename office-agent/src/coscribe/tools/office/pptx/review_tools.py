"""Toolkit methods for reading, previewing, delivery checks and theme colours."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_ooxml_valid
from . import toolkit_helpers as th
from .qa import (
    preview_deck,
)
from .theme import (
    THEME_SCHEME_SLOTS,
    parse_theme_color_slots,
    read_scheme_color,
    set_scheme_color,
)
from .toolkit_base import ToolkitBase

if TYPE_CHECKING:
    pass





class ReviewToolsMixin(ToolkitBase):
    @locked_by_path
    def check_pptx_delivery(self, path: str) -> dict[str, object]:
        import zipfile
        from collections import Counter

        file_path = self._check_readable(path)

        with zipfile.ZipFile(file_path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            name_counts = Counter(info.filename for info in infos)
            duplicate_parts = sorted(name for name, count in name_counts.items() if count > 1)
            try:
                corrupt_member = archive.testzip()
            except (NotImplementedError, RuntimeError) as exc:
                corrupt_member = f"<unreadable: {exc}>"
            media_infos = [info for info in infos if info.filename.startswith("ppt/media/")]
            media_total_bytes = sum(info.file_size for info in media_infos)
            media_largest = [
                {"part": info.filename, "bytes": info.file_size}
                for info in sorted(media_infos, key=lambda info: info.file_size, reverse=True)[
                    :5
                ]
            ]

        try:
            pptx_report = th.analyze_pptx_delivery(file_path)
        except Exception as exc:
            # A file broken enough that python-pptx itself can't fully
            # load/walk it (corrupt beyond just a duplicate/oversized
            # part -- python-pptx parses slide parts lazily, so this can
            # surface anywhere in th.analyze_pptx_delivery, not only at
            # Presentation() construction) must still return whatever
            # the raw-zip pass above already found, rather than crashing
            # this read-only audit outright -- hit for real against a
            # deliberately-corrupted test fixture, not a hypothetical.
            advisories: list[str] = []
            if corrupt_member:
                advisories.append(f"ZIP integrity failed at {corrupt_member!r}.")
            if duplicate_parts:
                advisories.append(f"Duplicate package parts: {', '.join(duplicate_parts)}.")
            advisories.append(
                f"Could not fully analyze this file as a presentation "
                f"({type(exc).__name__}: {exc}) -- only the raw package-level checks "
                "below could run."
            )
            return {
                "path": self._scope.relative(file_path),
                "zip_integrity": "corrupt" if corrupt_member else "ok",
                "corrupt_member": corrupt_member,
                "duplicate_parts": duplicate_parts,
                "slide_count": None,
                "hidden_slides": None,
                "fonts": None,
                "media": {
                    "count": len(media_infos),
                    "total_bytes": media_total_bytes,
                    "largest": media_largest,
                },
                "motion": None,
                "advisories": advisories,
            }

        advisories = []
        if corrupt_member:
            advisories.append(f"ZIP integrity failed at {corrupt_member!r}.")
        if duplicate_parts:
            advisories.append(f"Duplicate package parts: {', '.join(duplicate_parts)}.")
        if pptx_report["hidden_slides"]:
            advisories.append(
                f"{len(pptx_report['hidden_slides'])} hidden slide(s) won't show "
                f"during a normal slideshow: {pptx_report['hidden_slides']}."
            )
        if pptx_report["unsafe_fonts"]:
            advisories.append(
                f"Font(s) not on the common cross-platform-safe list: "
                f"{', '.join(pptx_report['unsafe_fonts'])} -- may substitute or render "
                "differently on a machine that doesn't have them installed."
            )
        if media_total_bytes > th.DELIVERY_MEDIA_ADVISORY_BYTES:
            advisories.append(
                f"Embedded media totals {media_total_bytes / 1_000_000:.1f}MB across "
                f"{len(media_infos)} file(s) -- consider compressing images before "
                "sending, especially by email."
            )

        return {
            "path": self._scope.relative(file_path),
            "zip_integrity": "corrupt" if corrupt_member else "ok",
            "corrupt_member": corrupt_member,
            "duplicate_parts": duplicate_parts,
            "slide_count": pptx_report["slide_count"],
            "hidden_slides": pptx_report["hidden_slides"],
            "fonts": {"used": pptx_report["fonts_used"], "unsafe": pptx_report["unsafe_fonts"]},
            "media": {
                "count": len(media_infos),
                "total_bytes": media_total_bytes,
                "largest": media_largest,
            },
            "motion": pptx_report["motion"],
            "advisories": advisories,
        }

    @locked_by_path
    def read_pptx_theme_colors(self, path: str) -> dict[str, object]:
        from lxml import etree
        from pptx import Presentation
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml.ns import qn

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        master = prs.slide_masters[0]
        theme_part = master.part.part_related_by(RT.THEME)
        root = etree.fromstring(theme_part.blob)
        clr_scheme = root.find(f".//{qn('a:clrScheme')}")
        colors: dict[str, object] = dict.fromkeys(THEME_SCHEME_SLOTS)
        if clr_scheme is not None:
            for slot in THEME_SCHEME_SLOTS:
                colors[slot] = read_scheme_color(clr_scheme, slot)
        return {"path": self._scope.relative(file_path), "colors": colors}

    @locked_by_path
    def edit_pptx_theme_colors(self, path: str, colors: str) -> dict[str, object]:
        from lxml import etree
        from pptx import Presentation
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml.ns import qn

        tokens = parse_theme_color_slots(colors)
        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        for master in prs.slide_masters:
            theme_part = master.part.part_related_by(RT.THEME)
            root = etree.fromstring(theme_part.blob)
            clr_scheme = root.find(f".//{qn('a:clrScheme')}")
            if clr_scheme is None:
                continue
            for slot, hex_value in tokens.items():
                set_scheme_color(clr_scheme, slot, hex_value)
            assert_ooxml_valid(root, "edit_pptx_theme_colors")
            theme_part._blob = etree.tostring(  # noqa: SLF001
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "colors": tokens}

    @locked_by_path
    def read_pptx(self, path: str, slide: Optional[int] = None) -> str:  # noqa: UP045
        from pptx import Presentation

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        slide_count = len(prs.slides)
        if slide is not None:
            if not 1 <= slide <= slide_count:
                raise ValueError(f"Slide {slide} out of range: deck has {slide_count} slides")
            return self._render_slide(prs.slides[slide - 1])
        return "\n\n---\n\n".join(
            self._render_slide(s, with_heading=True) for s in prs.slides
        )

    @locked_by_path
    def render_pptx_preview(self, path: str, max_slides: int = 8) -> dict[str, object]:
        file_path = self._check_readable(path)
        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        return preview_deck(file_path, state_dir, max_slides)

    @staticmethod
    def _render_slide(slide: Any, with_heading: bool = False) -> str:
        title_shape = slide.shapes.title
        title = title_shape.text if title_shape is not None else ""
        title_shape_id = title_shape.shape_id if title_shape is not None else None
        lines = [f"## {title}"] if with_heading else []
        for shape in th.leaf_shapes(slide.shapes):
            if title_shape_id is not None and shape.shape_id == title_shape_id:
                continue
            if shape.has_table:
                for row in shape.table.rows:
                    lines.append("| " + " | ".join(cell.text for cell in row.cells) + " |")
            elif shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text:
                        lines.append(f"- {paragraph.text}")
        return "\n".join(lines)
