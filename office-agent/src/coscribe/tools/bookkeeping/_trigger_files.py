"""Where a scheduled task's own files live: one name per task id, inside the store's folder."""

from __future__ import annotations

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
    return root / f"{trigger_id}{suffix}"
