"""Which Word, Excel and PowerPoint files a turn wrote that don't open.

A file the model wrote but the person can't open is the worst way for a turn to end: the reply
says it is done. At the end of a turn each Office file its calls wrote is opened the way the
office libraries open it, and the ones that fail go back to the model once (turn_checks.py)."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from langchain_core.messages import ToolMessage

from .tool_deferral import unwrap_use_tool_call

OFFICE_SUFFIXES = (".docx", ".xlsx", ".pptx")


def _office_paths(values: Any) -> list[str]:
    return [v for v in values if isinstance(v, str) and v.lower().endswith(OFFICE_SUFFIXES)]


def written_office_files(turn: Sequence[Any], writers: set[str]) -> list[str]:
    """The Office files named by this turn's writing calls that didn't fail, and those a script
    reported in its result's `files_written`, in order and once each."""
    # A call that failed wrote nothing, and the file it named may be one the person had already.
    failed = {m.tool_call_id for m in turn if isinstance(m, ToolMessage) and m.status == "error"}
    paths: list[str] = []
    for message in turn:
        for call in getattr(message, "tool_calls", None) or []:
            name, args = unwrap_use_tool_call(call["name"], call.get("args") or {})
            if name in writers and call.get("id") not in failed:
                paths += _office_paths(args.values())
        if isinstance(message, ToolMessage) and "files_written" in str(message.content):
            try:
                result = json.loads(str(message.content))
            except ValueError:
                continue
            if isinstance(result, dict):
                paths += _office_paths(result.get("files_written") or [])
    return list(dict.fromkeys(paths))


def why_it_does_not_open(path: Path) -> str | None:
    """None when the file opens; else what went wrong, in the library's words."""
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError as DocxPackageNotFound
    from openpyxl import load_workbook
    from pptx import Presentation
    from pptx.exc import PackageNotFoundError as PptxPackageNotFound

    failures = (
        OSError,
        ValueError,
        KeyError,
        SyntaxError,  # lxml's XMLSyntaxError
        zipfile.BadZipFile,
        DocxPackageNotFound,
        PptxPackageNotFound,
    )
    try:
        with zipfile.ZipFile(path) as archive:
            corrupt = archive.testzip()
        if corrupt:
            return f"the part {corrupt} is corrupt"
        suffix = path.suffix.lower()
        if suffix == ".docx":
            Document(str(path))
        elif suffix == ".xlsx":
            load_workbook(path, read_only=True).close()
        else:
            Presentation(str(path))
    except failures as exc:
        return f"{type(exc).__name__}: {exc}"[:300]
    return None


def broken_office_files(
    turn: Sequence[Any], writers: set[str], resolve_file: Callable[[str], Path]
) -> list[str]:
    """`path: why` for each Office file this turn wrote that exists and doesn't open."""
    broken = []
    for name in written_office_files(turn, writers):
        try:
            path = resolve_file(name)
        except (OSError, ValueError):
            continue
        if not path.is_file():
            continue
        why = why_it_does_not_open(path)
        if why:
            broken.append(f"- {name}: {why}")
    return broken
