"""Check, on a Windows machine, what coscribe does through Microsoft Office or WPS (decision 0012):
every conversion `convert_office_file` offers, the first-page previews of a Word, Excel and
PowerPoint file, and that a file the user has open in the program stays open.

CI's Windows runners have neither program, so these paths are faked in the tests; this script is
how they are checked for real. Run it from `office-agent/`, with nothing important unsaved in
Word, Excel or PowerPoint:

    python scripts/check_office.py              # a table of results; exit 1 if a check fails
    python scripts/check_office.py --require    # also exit 1 when no office program is found

It works in a fresh temporary folder (`--out DIR` keeps the files) and opens the user's own
files nowhere.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from coscribe.tools import _office_com, _thumbnail
from coscribe.tools.convert import build_convert_tools

SAMPLES = Path(__file__).resolve().parent / "office_check_samples"
MARKER = "Office check"

CONVERSIONS = (
    ("sample.doc", "docx"),
    ("sample.doc", "pdf"),
    ("sample.xls", "xlsx"),
    ("sample.xls", "pdf"),
    ("sample.ppt", "pptx"),
    ("sample.ppt", "pdf"),
    ("sample.docx", "pdf"),
    ("sample.xlsx", "pdf"),
    ("sample.pptx", "pdf"),
)
PREVIEWS = ("sample.docx", "sample.xlsx", "sample.pptx")

# (COM name, the collection of open files, how to open one) per program; the opened file is
# the user's stand-in, which a conversion in the same program must leave open.
_KEEPS_OPEN = {
    "word": ("Documents", "$app.Documents.Open($env:COSCRIBE_SOURCE) | Out-Null"),
    "excel": ("Workbooks", "$app.Workbooks.Open($env:COSCRIBE_SOURCE) | Out-Null"),
    "powerpoint": ("Presentations", "$app.Presentations.Open($env:COSCRIBE_SOURCE) | Out-Null"),
}
_PROCESSES = ("WINWORD.EXE", "EXCEL.EXE", "POWERPNT.EXE", "wps.exe", "et.exe", "wpp.exe")


@dataclass
class Result:
    case: str
    program: str
    status: str  # "ok", "FAIL" or "skip"
    seconds: float
    detail: str = ""


def write_modern_samples(folder: Path) -> None:
    from docx import Document
    from openpyxl import Workbook
    from pptx import Presentation

    document = Document()
    document.add_heading(MARKER, 1)
    document.add_paragraph("A Word file. 中文段落。")
    document.save(str(folder / "sample.docx"))

    book = Workbook()
    sheet = book.active
    for row in (["Region", "Revenue"], [MARKER, 120], ["South", 80], ["Total", "=SUM(B2:B3)"]):
        sheet.append(row)
    book.save(str(folder / "sample.xlsx"))

    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = MARKER
    slide.placeholders[1].text = "A PowerPoint file"
    deck.save(str(folder / "sample.pptx"))


def output_problem(path: Path) -> str:
    """What is wrong with a converted file, or "" when it opens and holds the sample's text."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pypdfium2

        pdf = pypdfium2.PdfDocument(str(path))
        if len(pdf) == 0:
            return "the PDF has no pages"
        text = "".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
        return "" if MARKER.lower() in text.lower() else "the PDF lacks the sample's text"
    if suffix == ".docx":
        from docx import Document

        text = "\n".join(p.text for p in Document(str(path)).paragraphs)
    elif suffix == ".xlsx":
        from openpyxl import load_workbook

        sheet = load_workbook(str(path)).active
        if sheet is None:
            return "the workbook has no sheet"
        text = "\n".join(str(cell.value) for row in sheet.iter_rows() for cell in row)
    else:
        from pptx import Presentation

        deck = Presentation(str(path))
        text = "\n".join(
            shape.text_frame.text
            for slide in deck.slides
            for shape in slide.shapes
            if shape.has_text_frame
        )
    return "" if MARKER.lower() in text.lower() else f"the {suffix} lacks the sample's text"


def powershell(code: str, env: dict[str, str], *, check: bool = True) -> str:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", code],
        capture_output=True,
        timeout=120,
        env={**os.environ, **env},
        check=check,
    )
    return completed.stdout.decode(errors="replace").strip()


def running_office_processes() -> set[str]:
    if sys.platform != "win32":
        return set()
    listing = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True)
    names = {line.split(",")[0].strip('"').lower() for line in listing.stdout.splitlines()}
    return {name for name in _PROCESSES if name.lower() in names}


def _timed(case: str, program: str, check: Callable[[], str]) -> Result:
    start = time.monotonic()
    try:
        problem = check()
    except Exception as error:  # noqa: BLE001 -- every failure is one row of the report
        problem = f"{type(error).__name__}: {error}"
    seconds = time.monotonic() - start
    return Result(case, program, "FAIL" if problem else "ok", seconds, problem)


def check_conversion(work: Path, source: str, to_format: str) -> Result:
    (convert,) = build_convert_tools(work)
    program = _office_com.program_for(work / source) or "-"
    output = f"{Path(source).stem}-{Path(source).suffix[1:]}.{to_format}"

    def run() -> str:
        result = convert(path=source, to_format=to_format, output_path=output)
        return output_problem(work / str(result["path"]))

    return _timed(f"{source} -> {to_format}", program, run)


def check_preview(work: Path, source: str) -> Result:
    program = _office_com.program_for(work / source) or "-"

    def run() -> str:
        name, reason = _thumbnail.render_thumbnail(work / source, work / "state")
        return "" if name else f"no preview: {reason}"

    return _timed(f"preview {source}", program, run)


def check_users_file_stays_open(work: Path, kind: str, source: str) -> Result:
    """Opens `source` in the program as the user would, converts another file of the same kind,
    and checks the first is still open; then closes it."""
    program = _office_com.program_for(work / source) or "-"
    collection, open_code = _KEEPS_OPEN[kind]
    user_copy = work / f"user-{source}"
    shutil.copy(work / source, user_copy)
    env = {"COSCRIBE_SOURCE": str(user_copy.resolve()), "COSCRIBE_PROG": program}
    attach = "$app = [Runtime.InteropServices.Marshal]::GetActiveObject($env:COSCRIBE_PROG)\n"
    is_open = (
        attach + f"@($app.{collection} | Where-Object {{ $_.FullName -eq $env:COSCRIBE_SOURCE }})"
        ".Count"
    )

    def run() -> str:
        powershell(
            "$app = New-Object -ComObject $env:COSCRIBE_PROG\n$app.Visible = $true\n" + open_code,
            env,
        )
        try:
            (convert,) = build_convert_tools(work)
            convert(path=source, to_format="pdf", output_path=f"while-open-{kind}.pdf")
            if powershell(is_open, env) != "1":
                return "the user's file was closed by the conversion"
            return ""
        finally:
            close = attach + (
                f"$app.{collection} | Where-Object {{ $_.FullName -eq $env:COSCRIBE_SOURCE }} "
                "| ForEach-Object { $_.Close() }\n"
                f"if ($app.{collection}.Count -eq 0) {{ $app.Quit() }}"
            )
            powershell(close, env, check=False)

    return _timed(f"{source} stays open", program, run)


def run_checks(work: Path) -> list[Result]:
    for legacy in SAMPLES.iterdir():
        shutil.copy(legacy, work / legacy.name)
    write_modern_samples(work)
    before = running_office_processes()

    results = [check_conversion(work, source, fmt) for source, fmt in CONVERSIONS]
    results += [check_preview(work, source) for source in PREVIEWS]
    # Checked before the open-file cases below, which start the programs themselves.
    time.sleep(5)  # Office takes a moment to exit after Quit.
    left = running_office_processes() - before
    results.append(
        Result(
            "no program left running",
            "-",
            "FAIL" if left else "ok",
            0.0,
            f"still running: {', '.join(sorted(left))}" if left else "",
        )
    )
    for kind, source in (
        ("word", "sample.docx"),
        ("excel", "sample.xlsx"),
        ("powerpoint", "sample.pptx"),
    ):
        if _office_com.program_for(work / source) is None:
            results.append(Result(f"{source} stays open", "-", "skip", 0.0, "no program"))
        else:
            results.append(check_users_file_stays_open(work, kind, source))
    return results


def report(results: list[Result]) -> str:
    rows = [f"{'check':34} {'program':24} {'result':6} {'seconds':>7}  detail"]
    rows += [
        f"{r.case:34} {r.program:24} {r.status:6} {r.seconds:7.1f}  {r.detail}" for r in results
    ]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, help="keep the files in this folder")
    parser.add_argument(
        "--require", action="store_true", help="exit 1 when no office program is found"
    )
    args = parser.parse_args(argv)

    found = {
        kind: _office_com.program_for(Path(f"x{suffix}"))
        for kind, suffix in (("Word", ".docx"), ("Excel", ".xlsx"), ("PowerPoint", ".pptx"))
    }
    print("Programs: " + ", ".join(f"{k} {v or 'not found'}" for k, v in found.items()))
    if not any(found.values()):
        print("Neither Microsoft Office nor WPS Office is installed: nothing to check.")
        return 1 if args.require else 0

    work = args.out or Path(tempfile.mkdtemp(prefix="coscribe_office_check_"))
    work.mkdir(parents=True, exist_ok=True)
    results = run_checks(work)
    print(report(results))
    print(f"Files: {work}")
    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
