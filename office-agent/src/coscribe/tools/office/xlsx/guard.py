"""What an edit through openpyxl would lose from a user's workbook.

openpyxl drops what it cannot read (sparklines, Excel 2010 conditional-format extensions,
slicers, form controls, VBA unless kept) and warns while loading; the parts of the file before
and after the save show the rest. A write that would lose something goes to a copy instead
(decision 0011), so the user's own file is never saved short of what it had."""

from __future__ import annotations

import re
import warnings
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

# A file's parts by what they hold; a kind that has fewer parts after the save was lost.
_PART_KINDS = {
    "xl/charts/chart": "charts",
    "xl/drawings/drawing": "drawings",
    "xl/media/": "pictures",
    "xl/pivotTables/": "pivot tables",
    "xl/pivotCache/": "pivot caches",
    "xl/tables/": "tables",
    "xl/comments": "comments",
    "xl/slicers/": "slicers",
    "xl/slicerCaches/": "slicers",
    "xl/timelines/": "timelines",
    "xl/ctrlProps/": "form controls",
    "xl/vbaProject.bin": "macros",
    "xl/externalLinks/": "links to other files",
    "xl/threadedComments/": "threaded comments",
}
_EXTENSION = re.compile(rb"<(?:\w+:)?ext\s[^>]*uri=")


def inventory(path: Path) -> Counter[str]:
    """How many of each kind of part the file has, and how many extensions its sheets carry."""
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            for prefix, kind in _PART_KINDS.items():
                if name.startswith(prefix):
                    counts[kind] += 1
            if name.startswith("xl/worksheets/sheet"):
                counts["sheet extensions"] += len(_EXTENSION.findall(archive.read(name)))
    return counts


def load_watching(path: Path) -> tuple[Any, list[str]]:
    """The workbook, and the features openpyxl says it will drop when it saves."""
    from openpyxl import load_workbook

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        workbook = load_workbook(str(path), keep_vba=path.suffix.lower() == ".xlsm")
    dropped = sorted(
        {
            str(w.message).split(" is not supported")[0]
            for w in caught
            if "will be removed" in str(w.message)
        }
    )
    return workbook, dropped


def losses(
    before: Counter[str], after: Counter[str], dropped: list[str], deleted_sheets: bool
) -> list[str]:
    """What the saved file lacks. Deleting a sheet removes its parts on purpose, so only
    openpyxl's own warnings count then."""
    lost = [f"{name} (openpyxl cannot keep it)" for name in dropped]
    if not deleted_sheets:
        lost += [
            f"{kind}: {before[kind]} -> {after[kind]}"
            for kind in sorted(before)
            if after[kind] < before[kind]
        ]
    return lost


def copy_path(path: Path) -> Path:
    """`budget.xlsx` -> `budget (coscribe).xlsx`, numbered if that is taken."""
    candidate = path.with_name(f"{path.stem} (coscribe){path.suffix}")
    number = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} (coscribe {number}){path.suffix}")
        number += 1
    return candidate
