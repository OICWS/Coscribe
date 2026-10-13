"""A produced file as pictures: the pages a person would see, for the judge and the checks."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any


def render_pages(path: Path, out_dir: Path) -> dict[str, Any]:
    """The file as one PNG per page (`page-01.png`...) through LibreOffice; `pdf` is kept
    for the overflow check."""
    from coscribe.tools._thumbnail import _convert_to_pdf, _render_pdf_pages

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coscribe_eval_") as scratch:
        pdf = _convert_to_pdf(path, Path(scratch))
        if pdf is None:
            return {"ok": False, "reason": "LibreOffice did not produce a PDF", "pages": []}
        kept_pdf = out_dir / "deck.pdf"
        kept_pdf.write_bytes(pdf.read_bytes())
        for old in out_dir.glob("page-*.png"):
            old.unlink()
        try:
            rendered = _render_pdf_pages(pdf, Path(scratch), 1, 10_000)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "reason": f"{type(exc).__name__}: {exc}",
                "pages": [],
                "pdf": kept_pdf.name,
            }
        pages = []
        for number, png in enumerate(rendered, start=1):
            target = out_dir / f"page-{number:02d}.png"
            target.write_bytes(png.read_bytes())
            pages.append(target.name)
    return {"ok": True, "pages": pages, "pdf": kept_pdf.name}
