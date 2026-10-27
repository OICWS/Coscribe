"""What the person changed in a Doc in the app since coscribe last knew it (decision 0025, as 0019
does for Word files). The editor's route remembers the blocks before its first save; at the start
of coscribe's next turn the file is compared with that, and the net difference is told once. An edit
that was undone is not reported."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path

from ..._file_locks import file_lock
from .blocks import read_doc

_FOLDER = "doc_edits"
_SHOWN = 80
_MAX_ITEMS = 12
# Two lines must read this alike to count as one line edited, not one removed and one added.
_ALIKE = 0.5


def _record_of(path: Path, state_dir: Path) -> Path:
    key = hashlib.sha1(os.path.normcase(str(path.resolve())).encode("utf-8")).hexdigest()[:20]
    return state_dir / _FOLDER / f"{key}.json"


def _lines(path: Path) -> list[str]:
    """One line per block: its kind and its words, so a change of either shows."""
    doc = read_doc(path.read_text(encoding="utf-8"))
    return [f"{b.kind}: {' '.join(b.text.split())}" for b in doc.blocks]


def remember_before_edit(path: Path, state_dir: Path) -> None:
    """Called before the editor writes: the first call since coscribe was last told keeps the file
    as it is now; later ones change nothing."""
    record = _record_of(path, state_dir)
    with file_lock(record):
        if record.exists():
            return
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            json.dumps({"path": str(path), "lines": _lines(path)}, ensure_ascii=False),
            encoding="utf-8",
        )


def _shown(line: str) -> str:
    return line if len(line) <= _SHOWN else line[: _SHOWN - 1] + "…"


def edits_since_told(path: Path, state_dir: Path) -> dict[str, list[str]] | None:
    """What was changed, added and removed since the remembered state, None when there is nothing
    to tell. Telling it forgets the state: the next call has nothing until the person edits
    again."""
    record = _record_of(path, state_dir)
    with file_lock(record):
        try:
            before = json.loads(record.read_text(encoding="utf-8"))["lines"]
        except (OSError, ValueError, KeyError):
            return None
        record.unlink(missing_ok=True)
    after = _lines(path)
    changed: list[str] = []
    added: list[str] = []
    removed: list[str] = []
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            _pair(before[i1:i2], after[j1:j2], changed, removed, added)
    if not (changed or added or removed):
        return None
    return {"changed": _cut(changed), "added": _cut(added), "removed": _cut(removed)}


def _pair(
    old: list[str], new: list[str], changed: list[str], removed: list[str], added: list[str]
) -> None:
    """Lines of a differing stretch: an old line and a later new one that read alike are one line
    changed; the old lines left are removed, the new ones left are added."""
    at = 0
    for line in old:
        match = next(
            (
                j
                for j in range(at, len(new))
                if difflib.SequenceMatcher(None, line, new[j]).ratio() >= _ALIKE
            ),
            None,
        )
        if match is None:
            removed.append(_shown(line))
            continue
        added.extend(_shown(skipped) for skipped in new[at:match])
        changed.append(f"{_shown(line)} -> {_shown(new[match])}")
        at = match + 1
    added.extend(_shown(line) for line in new[at:])


def _cut(items: list[str]) -> list[str]:
    return items[:_MAX_ITEMS] + (
        [f"and {len(items) - _MAX_ITEMS} more"] if len(items) > _MAX_ITEMS else []
    )
