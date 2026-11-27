"""A deck slide previewed from the SVG it was compiled from (decision 0012), with resvg: no office
program is needed."""

from __future__ import annotations

from pathlib import Path

PREVIEW_WIDTH = 1280


def render_page(svg: str, pictures: Path, target: Path, width: int = PREVIEW_WIDTH) -> None:
    """Writes the slide `svg` as a PNG, its pictures read from the folder `pictures`. Raises
    ValueError (resvg's own error) or ET.ParseError when the page cannot be drawn."""
    import resvg_py

    png = resvg_py.svg_to_bytes(
        svg_string=svg,
        width=width,
        resources_dir=str(pictures),
        background="#ffffff",
    )
    target.write_bytes(bytes(png))
