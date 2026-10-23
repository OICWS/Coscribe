"""PDFium is not thread-safe: two threads using it at once crash the process, and the Slides
panel asks for every thumbnail of a deck at once. Every caller keeps its lock held while a PDFium
document is open."""

from pathlib import Path
from typing import Any

import pypdfium2
import pytest
from PIL import Image

from coscribe.tools._pdfium import PDFIUM_LOCK
from coscribe.tools._thumbnail import _render_pdf_pages
from coscribe.tools.office.pptx.engine import view_foreign


class _Bitmap:
    def to_pil(self) -> Image.Image:
        return Image.new("RGB", (8, 4))


class _Page:
    def get_size(self) -> tuple[float, float]:
        assert PDFIUM_LOCK._is_owned()  # type: ignore[attr-defined]
        return 8.0, 4.0

    def render(self, scale: float = 1.0) -> _Bitmap:
        assert PDFIUM_LOCK._is_owned()  # type: ignore[attr-defined]
        return _Bitmap()


class _Document:
    """Fails the test when it is used without the lock."""

    def __init__(self, path: str) -> None:
        assert PDFIUM_LOCK._is_owned()  # type: ignore[attr-defined]

    def __len__(self) -> int:
        assert PDFIUM_LOCK._is_owned()  # type: ignore[attr-defined]
        return 1

    def __getitem__(self, index: int) -> _Page:
        assert PDFIUM_LOCK._is_owned()  # type: ignore[attr-defined]
        return _Page()

    def close(self) -> None:
        assert PDFIUM_LOCK._is_owned()  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def _fake_pdfium(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pypdfium2, "PdfDocument", _Document)


def test_a_foreign_slide_is_drawn_with_the_pdfium_lock_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(view_foreign, "_pdf", lambda deck, state_dir: tmp_path / "deck.pdf")

    svg = view_foreign.foreign_slide_svg(tmp_path / "deck.pptx", 0, tmp_path)

    assert svg.startswith("<svg")


def test_pdf_pages_for_a_preview_are_rendered_with_the_pdfium_lock_held(tmp_path: Path) -> None:
    files: list[Any] = _render_pdf_pages(tmp_path / "deck.pdf", tmp_path, 1, 1)

    assert [f.name for f in files] == ["page-0001.png"]
