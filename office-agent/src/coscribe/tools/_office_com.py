"""Converting a Word, Excel or PowerPoint file with the office program installed on Windows,
through COM (decision 0012): Microsoft Office, or WPS Office, which registers the same object
model under its own names.

The job runs in a PowerShell process, which every Windows has: no Python COM package is needed,
and a hung job can be killed on a timeout, PowerShell and the office program COM started for it.
Paths reach the script through environment variables, never inside its text, so no file name can
change what it runs."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from ._office_bins import kill_tree, run_killable, run_until_marker

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
# closing or hiding the one the user works in would take their presentations with it. The close
# sits in a `finally` so that a file the program cannot open does not leave it running hidden.
# The script prints `_SAVED` once the file is written and closed: the program takes another 2-3 s
# to exit after Quit (Word 16, measured 2026-11), and the caller need not wait for that.
# A Word PDF is the final text without markup: the default export follows the screen's markup
# view, which shrinks every page beside a grey comment pane. WPS may lack the view filter or the
# export call, so it keeps its own save.
_OPEN_AND_SAVE = {
    "word": """
$open = $app.Documents.Count
if ($open -eq 0) { $app.Visible = $false; $app.DisplayAlerts = 0 }
try {
  $doc = $app.Documents.Open($env:COSCRIBE_SOURCE, $false, $true, $false)
  try {
    if ($env:COSCRIBE_FORMAT -eq '17') {
      try {
        $doc.ActiveWindow.View.RevisionsFilter.Markup = 0
        $doc.ActiveWindow.View.RevisionsFilter.View = 0
        $doc.ExportAsFixedFormat($env:COSCRIBE_TARGET, 17, $false, 0, 0, 1, 1, 0)
      } catch { $doc.SaveAs2($env:COSCRIBE_TARGET, 17) }
    } else { $doc.SaveAs2($env:COSCRIBE_TARGET, [int]$env:COSCRIBE_FORMAT) }
  } finally { $doc.Close($false) }
  [Console]::Out.WriteLine('coscribe-saved'); [Console]::Out.Flush()
} finally { if ($open -eq 0) { $app.Quit() } }
""",
    "excel": """
$open = $app.Workbooks.Count
if ($open -eq 0) { $app.Visible = $false; $app.DisplayAlerts = $false }
try {
  $book = $app.Workbooks.Open($env:COSCRIBE_SOURCE, 0, $true)
  try {
    if ($env:COSCRIBE_FORMAT -eq 'pdf') { $book.ExportAsFixedFormat(0, $env:COSCRIBE_TARGET) }
    else { $book.SaveAs($env:COSCRIBE_TARGET, [int]$env:COSCRIBE_FORMAT) }
  } finally { $book.Close($false) }
  [Console]::Out.WriteLine('coscribe-saved'); [Console]::Out.Flush()
} finally { if ($open -eq 0) { $app.Quit() } }
""",
    "powerpoint": """
$open = $app.Presentations.Count
try {
  $deck = $app.Presentations.Open($env:COSCRIBE_SOURCE, -1, 0, 0)
  try { $deck.SaveAs($env:COSCRIBE_TARGET, [int]$env:COSCRIBE_FORMAT) } finally { $deck.Close() }
  [Console]::Out.WriteLine('coscribe-saved'); [Console]::Out.Flush()
} finally { if ($open -eq 0) { $app.Quit() } }
""",
}

# The program file behind each COM name. COM starts an office program for a script with
# `-Embedding` on its command line and as a child of its own service, not of PowerShell, so
# killing PowerShell's tree on a timeout leaves the program running, hidden, with the file open.
_IMAGES = {
    "Word.Application": "WINWORD.EXE",
    "KWps.Application": "wps.exe",
    "Excel.Application": "EXCEL.EXE",
    "Ket.Application": "et.exe",
    "PowerPoint.Application": "POWERPNT.EXE",
    "Kwpp.Application": "wpp.exe",
}

# Ends the copies of the program that COM started since the job began. One the user opened has
# no `-Embedding`, and one that was already running (the user's PowerPoint, which a script
# shares) is older than the job, so neither is touched.
_END_STARTED_FOR_JOB = """
$since = [datetime]::Parse($env:COSCRIBE_SINCE).ToUniversalTime()
Get-CimInstance Win32_Process -Filter "Name='$env:COSCRIBE_IMAGE'" |
  Where-Object {
    $_.CommandLine -like '*Embedding*' -and $_.CreationDate.ToUniversalTime() -ge $since
  } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
"""

# Office shows one document at a time well; parallel jobs in one instance fail at random.
_LOCK = threading.Lock()
_SAVED = "coscribe-saved"
# The previous job's program, still exiting after it saved; the next job waits for it, under _LOCK,
# so two jobs never share one instance.
_exiting: threading.Thread | None = None


def _registered(prog_id: str) -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\CLSID"):
            return True
    except OSError:
        return False


def installed_office() -> str | None:
    """The office program that converts before LibreOffice is tried, by its product name, or
    None: Microsoft Office over WPS, as `program_for` picks them."""
    if shutil.which("powershell") is None:
        return None
    for index, name in enumerate(("Microsoft Office", "WPS Office")):
        if any(_registered(names[index]) for names in _PROGRAMS.values()):
            return name
    return None


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


def _end_started_since(prog_id: str, started: datetime) -> None:
    """Ends what COM started for a job that ran out of time; best effort, since the job has
    already failed and the person is told so either way."""
    env = {**os.environ, "COSCRIBE_SINCE": started.isoformat(), "COSCRIBE_IMAGE": _IMAGES[prog_id]}
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", _END_STARTED_FOR_JOB]
    with contextlib.suppress(subprocess.SubprocessError, OSError):
        run_killable(command, 30, env=env)


def _let_exit(
    process: subprocess.Popen[bytes], deadline: float, prog_id: str, started: datetime
) -> None:
    """Waits for a job that already saved its file to end, within the job's own time."""
    try:
        process.wait(max(deadline - time.monotonic(), 1.0))
    except subprocess.TimeoutExpired:
        kill_tree(process)
        _end_started_since(prog_id, started)


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
    global _exiting
    with _LOCK:
        if _exiting is not None:
            _exiting.join()
            _exiting = None
        started = datetime.now(UTC)
        deadline = time.monotonic() + timeout
        try:
            still_running = run_until_marker(command, timeout, _SAVED, env=env)
        except subprocess.TimeoutExpired:
            _end_started_since(prog_id, started)
            raise ValueError(f"{prog_id} took too long to convert this file.") from None
        except (subprocess.CalledProcessError, OSError) as error:
            detail = getattr(error, "stderr", b"") or b""
            message = detail.decode(errors="replace").strip().splitlines()
            raise ValueError(
                f"{prog_id} could not convert this file: {message[0] if message else error}"
            ) from None
        if still_running is not None:
            _exiting = threading.Thread(
                target=_let_exit, args=(still_running, deadline, prog_id, started), daemon=True
            )
            _exiting.start()
    if not target.is_file():
        raise ValueError(f"{prog_id} produced no file.")
    return prog_id
