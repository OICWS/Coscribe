"""Whether a working LibreOffice is here, for the tests that use it as an independent reader of
the files the tools write (decision 0012 keeps it for development and the evaluation only)."""

from __future__ import annotations

import functools
import shutil
import tempfile
from pathlib import Path


@functools.cache
def libreoffice_works() -> bool:
    """A binary on PATH is not enough: a broken font setup or a sandbox converts nothing, and a
    test gated on it should skip rather than fail."""
    from docx import Document

    from evals.libreoffice import convert_to_pdf

    probe = Path(tempfile.mkdtemp(prefix="coscribe_lo_probe_"))
    try:
        Document().save(str(probe / "probe.docx"))
        return convert_to_pdf(probe / "probe.docx", probe) is not None
    finally:
        shutil.rmtree(probe, ignore_errors=True)


def libreoffice_as_office(source: Path, target: Path, to_format: str, timeout: float) -> str | None:
    """`_office_com.convert` with LibreOffice standing in for Office, for the tests that check a
    preview or a conversion end to end where no Office is installed (CI, this container)."""
    from evals.libreoffice import convert_to_pdf

    if to_format != "pdf":
        return None
    produced = convert_to_pdf(source, target.parent, timeout)
    if produced is None:
        raise ValueError("LibreOffice could not convert this file")
    if produced != target:
        produced.replace(target)
    return "LibreOffice (test stand-in)"


def convert_with_libreoffice(source: Path, out_dir: Path, timeout: float = 120.0) -> Path:
    """`source` as a PDF in `out_dir`, through a LibreOffice profile no other worker holds.

    A test that runs `soffice` itself uses the shared default profile: parallel pytest workers
    then hand each other their jobs and some convert nothing (#399)."""
    from evals.libreoffice import convert_to_pdf

    produced = convert_to_pdf(source, out_dir, timeout)
    assert produced is not None, f"LibreOffice could not convert {source.name}"
    return produced
