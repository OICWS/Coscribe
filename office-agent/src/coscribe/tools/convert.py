"""Converting between Office formats with the office program installed: Microsoft Office or
WPS, through COM (decision 0012).

Two jobs people ask for constantly and nothing else here does: open a legacy
file (.xls, .doc, .ppt -- the readers only take the OOXML formats) and
export a document, workbook or deck as a PDF.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ..runtime import tool_metadata
from . import _office_com
from ._workspace import WorkspaceScope

# What each source type can become. Legacy and OpenDocument files can be
# brought up to the OOXML format; any Office file can be exported to PDF.
_TARGETS: dict[str, frozenset[str]] = {
    ".doc": frozenset({"docx", "pdf"}),
    ".rtf": frozenset({"docx", "pdf"}),
    ".odt": frozenset({"docx", "pdf"}),
    ".docx": frozenset({"pdf"}),
    ".xls": frozenset({"xlsx", "pdf"}),
    ".ods": frozenset({"xlsx", "pdf"}),
    ".xlsx": frozenset({"pdf"}),
    ".ppt": frozenset({"pptx", "pdf"}),
    ".odp": frozenset({"pptx", "pdf"}),
    ".pptx": frozenset({"pdf"}),
}

# A big deck or workbook takes a while; the first start of the program after a login takes
# longer still.
_CONVERT_TIMEOUT = 180.0


class ConvertToolkit:
    def __init__(
        self,
        root: str | Path,
        extra_readable: Sequence[str | Path] = (),
        extra_writable: Sequence[str | Path] = (),
    ) -> None:
        self._scope = WorkspaceScope(
            root, extra_readable=extra_readable, extra_writable=extra_writable
        )

    def convert_office_file(
        self, path: str, to_format: str, output_path: str = ""
    ) -> dict[str, object]:
        source = self._scope.resolve(path)
        if not source.is_file():
            raise ValueError(f"File does not exist: {path}")
        target_format = to_format.strip().lower().lstrip(".")
        allowed = _TARGETS.get(source.suffix.lower())
        if allowed is None:
            raise ValueError(
                f"{source.suffix or 'This file'} isn't a type convert_office_file handles "
                f"({', '.join(sorted(_TARGETS))})."
            )
        if target_format not in allowed:
            raise ValueError(
                f"A {source.suffix} file can become: {', '.join(sorted(allowed))} "
                f"(not {to_format!r})."
            )
        destination = (
            self._scope.resolve(output_path, write=True)
            if output_path
            else self._scope.resolve(str(source.with_suffix(f".{target_format}")), write=True)
        )
        if destination.suffix.lower() != f".{target_format}":
            raise ValueError(f"output_path must end in .{target_format}")
        if destination.exists():
            raise FileExistsError(
                f"{self._scope.relative(destination)} already exists -- pick another "
                "output_path rather than replacing it."
            )
        work = Path(tempfile.mkdtemp(prefix="coscribe_convert_"))
        try:
            produced = work / f"{source.stem}.{target_format}"
            program = _office_com.convert(source, produced, target_format, _CONVERT_TIMEOUT)
            if program is None:
                raise ValueError(
                    "Converting needs Microsoft Office or WPS Office on this computer, and "
                    "neither was found."
                )
            if not produced.is_file():
                raise ValueError(
                    f"{program} produced no file -- the source may be damaged or "
                    "password-protected."
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(produced), str(destination))
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return {
            "path": self._scope.relative(destination),
            "bytes_written": destination.stat().st_size,
            "converted_from": self._scope.relative(source),
            "converted_by": program,
        }


def build_convert_tools(
    root: str | Path,
    *,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    toolkit = ConvertToolkit(root, extra_readable=extra_readable, extra_writable=extra_writable)

    def convert_office_file(path: str, to_format: str, output_path: str = "") -> dict[str, object]:
        """Convert an Office file to another format with the office program installed -- the
        way to open a legacy .xls/.doc/.ppt (the read tools take only
        .xlsx/.docx/.pptx: convert first, then read the new file) and the way
        to export a Word, Excel or PowerPoint file as a PDF.

        `.doc`/`.rtf`/`.odt` can become docx or pdf; `.xls`/`.ods` xlsx or
        pdf; `.ppt`/`.odp` pptx or pdf; `.docx`/`.xlsx`/`.pptx` pdf. The
        original is left as it is and an existing file is never replaced.

        Args:
            path: file to convert, relative to the workspace root
            to_format: "docx", "xlsx", "pptx" or "pdf"
            output_path: where to write the result; by default next to the
                original with the new extension
        """
        return toolkit.convert_office_file(path=path, to_format=to_format, output_path=output_path)

    return [
        tool_metadata(convert_office_file, risk_category="WRITE_LOCAL", category="documents"),
    ]
