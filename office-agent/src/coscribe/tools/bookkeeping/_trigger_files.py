"""Where a scheduled task's own files live: one name per task id, inside the store's folder."""

from __future__ import annotations

import os
import re
from pathlib import Path

# Letters, digits, `_` and `-`: no dot, slash or backslash. A task id comes from a URL path or a
# tool call, and on Windows a backslash in it (a URL carries one as %5C) reaches outside the folder.
_TRIGGER_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


def is_trigger_id(trigger_id: str) -> bool:
    return bool(_TRIGGER_ID.fullmatch(trigger_id))


def trigger_file(root: Path, trigger_id: str, suffix: str) -> Path:
    """`root/<trigger_id><suffix>`; ValueError for a name that is not a task id."""
    if not is_trigger_id(trigger_id):
        raise ValueError(f"{trigger_id!r} is not a task id")
    return file_in(root, f"{trigger_id}{suffix}")


def file_in(root: str | Path, name: str) -> Path:
    """`root/<name>`; ValueError when `name` would reach outside `root`.

    Callers check the name first; this repeats the check on the resolved path, in the form code
    scanning recognizes, so a later change to a caller's check can't open the store up."""
    folder = os.path.abspath(root)
    path = os.path.abspath(os.path.join(folder, name))
    if not path.startswith(os.path.join(folder, "")) or path == folder:
        raise ValueError(f"{name!r} is not a file name inside {folder}")
    return Path(path)
