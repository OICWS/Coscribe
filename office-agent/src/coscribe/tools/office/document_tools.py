"""The Word and PDF tools as one toolkit: `DocumentToolkit` and `build_document_tools`."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .docx import DocxToolkit, build_docx_tools
from .pdf import PdfToolkit, build_pdf_tools


class DocumentToolkit(DocxToolkit, PdfToolkit):
    """Both toolkits over one workspace scope."""


def build_document_tools(
    root: str | Path,
    *,
    state_dir: str | Path | None = None,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    """Return the tool callables the Coordinator agent can call, bound to `root`
    (plus any user-configured extra_readable/extra_writable directories)."""
    toolkit = DocumentToolkit(
        root, state_dir=state_dir, extra_readable=extra_readable, extra_writable=extra_writable
    )
    return [*build_docx_tools(toolkit), *build_pdf_tools(toolkit)]
