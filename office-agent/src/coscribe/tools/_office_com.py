"""Converting a Word, Excel or PowerPoint file with the office program installed on Windows,
through COM (decision 0012): Microsoft Office, or WPS Office, which registers the same object
model under its own names.

The job runs in a PowerShell process, which every Windows has: no Python COM package is needed,
and a hung job can be killed on a timeout like any other process. Paths reach the script through
environment variables, never inside its text, so no file name can change what it runs."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from ._office_bins import run_soffice

# The program that opens each type, Microsoft's name first, then WPS's.
_PROGRAMS: dict[str, tuple[str, ...]] = {
    "word": ("Word.Application", "KWps.Application"),
    "excel": ("Excel.Application", "Ket.Application"),
    "powerpoint": ("PowerPoint.Application", "Kwpp.Application"),
}
_KIND = {
    **dict.fromkeys((".doc", ".docx", ".rtf", ".odt"), "word"),
    **dict.fromkeys((".xls", ".xlsx", ".ods"), "excel"),
    **dict.fromkeys((".ppt", ".pptx", ".odp"), "powerpoint"),
}
# The file-format numbers of each object model's save call (WdSaveFormat, XlFileFormat,
# PpSaveAsFileType).
_FORMATS = {
    ("word", "pdf"): 17,
    ("word", "docx"): 16,
    ("excel", "xlsx"): 51,
    ("powerpoint", "pdf"): 32,
    ("powerpoint", "pptx"): 24,
}

# Each script opens the file read-only and without a window. It hides the program, and closes
# it, only when no file of the user's is open in it: PowerPoint has one instance per user, and
# closing or hiding the one the user works in would take their presentations with it.
_OPEN_AND_SAVE = {
    "word": """
$open = $app.Documents.Count
if ($open -eq 0) { $app.Visible = $false; $app.DisplayAlerts = 0 }
$doc = $app.Documents.Open($env:COSCRIBE_SOURCE, $false, $true, $false)
try { $doc.SaveAs2($env:COSCRIBE_TARGET, [int]$env:COSCRIBE_FORMAT) } finally { $doc.Close($false) }
if ($open -eq 0) { $app.Quit() }
""",
    "excel": """
$open = $app.Workbooks.Count
if ($open -eq 0) { $app.Visible = $false; $app.DisplayAlerts = $false }
$book = $app.Workbooks.Open($env:COSCRIBE_SOURCE, 0, $true)
try {
  if ($env:COSCRIBE_FORMAT -eq 'pdf') { $book.ExportAsFixedFormat(0, $env:COSCRIBE_TARGET) }
  else { $book.SaveAs($env:COSCRIBE_TARGET, [int]$env:COSCRIBE_FORMAT) }
} finally { $book.Close($false) }
if ($open -eq 0) { $app.Quit() }
""",
    "powerpoint": """
$open = $app.Presentations.Count
$deck = $app.Presentations.Open($env:COSCRIBE_SOURCE, -1, 0, 0)
try { $deck.SaveAs($env:COSCRIBE_TARGET, [int]$env:COSCRIBE_FORMAT) } finally { $deck.Close() }
if ($open -eq 0) { $app.Quit() }
""",
}

# Office shows one document at a time well; parallel jobs in one instance fail at random.
_LOCK = threading.Lock()


def _registered(prog_id: str) -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\CLSID"):
            return True
    except OSError:
        return False


def program_for(source: Path) -> str | None:
    """The COM name of the installed program that opens `source`, or None."""
    kind = _KIND.get(source.suffix.lower())
    if kind is None or shutil.which("powershell") is None:
        return None
    return next((p for p in _PROGRAMS[kind] if _registered(p)), None)


def script(source: Path, prog_id: str) -> str:
    """The PowerShell that opens `source` in `prog_id` and saves the target the environment
    names."""
    kind = _KIND[source.suffix.lower()]
    return (
        "$ErrorActionPreference = 'Stop'\n"
        f"$app = New-Object -ComObject '{prog_id}'\n" + _OPEN_AND_SAVE[kind]
    )


def convert(source: Path, target: Path, to_format: str, timeout: float) -> str | None:
    """Writes `source` as `to_format` ("pdf", "docx", "xlsx" or "pptx") to `target` with the
    installed office program. Returns the program's COM name, or None when no program can do it.
    Raises ValueError when the program fails or takes longer than `timeout` seconds."""
    prog_id = program_for(source)
    kind = _KIND.get(source.suffix.lower())
    if prog_id is None or kind is None:
        return None
    code = "pdf" if (kind, to_format) == ("excel", "pdf") else _FORMATS.get((kind, to_format))
    if code is None:
        return None
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script(source, prog_id)]
    env = {
        **os.environ,
        "COSCRIBE_SOURCE": str(source.resolve()),
        "COSCRIBE_TARGET": str(target.resolve()),
        "COSCRIBE_FORMAT": str(code),
    }
    with _LOCK:
        try:
            run_soffice(command, timeout, env=env)
        except subprocess.TimeoutExpired:
            raise ValueError(f"{prog_id} took too long to convert this file.") from None
        except (subprocess.CalledProcessError, OSError) as error:
            detail = getattr(error, "stderr", b"") or b""
            message = detail.decode(errors="replace").strip().splitlines()
            raise ValueError(
                f"{prog_id} could not convert this file: {message[0] if message else error}"
            ) from None
    if not target.is_file():
        raise ValueError(f"{prog_id} produced no file.")
    return prog_id
