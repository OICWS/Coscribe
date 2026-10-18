"""Comments on a deck's slides (design §5): kept in `comments.json` in the deck's pages folder, so
they travel with the deck and outlive the app. They stay in the app; the .pptx never holds them
(decision 0015).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...._file_locks import file_lock, replace_with_retry
from .view import NotBuiltFromPages, pages_folder

COMMENTS = "comments.json"
_MAX_TEXT = 4000


class CommentNotFound(KeyError):
    """No comment with that id on this deck."""


def read_comments(deck: Path) -> list[dict[str, Any]]:
    """The deck's comments, oldest first."""
    return _load(_store(deck))


def add_comment(
    deck: Path,
    *,
    slide: str,
    x: float,
    y: float,
    element: str,
    text: str,
    author: str,
    sent: bool,
) -> dict[str, Any]:
    """A new comment on `slide` (a page name without its suffix) at `x`, `y` (fractions of the
    slide), on the element named `element`. `sent` says it went to coscribe as a message."""
    comment = {
        "id": uuid.uuid4().hex[:12],
        "slide": slide,
        "x": min(max(float(x), 0.0), 1.0),
        "y": min(max(float(y), 0.0), 1.0),
        "element": element[:200],
        "text": _text(text),
        "author": author[:80],
        "created": _now(),
        "sent": sent,
        "resolved": False,
        "replies": [],
    }
    _change(deck, lambda comments: comments.append(comment))
    return comment


def reply_to_comment(deck: Path, comment_id: str, *, text: str, author: str) -> dict[str, Any]:
    reply = {"author": author[:80], "text": _text(text), "created": _now()}
    _change(deck, lambda comments: _find(comments, comment_id)["replies"].append(reply))
    return reply


def resolve_comment(deck: Path, comment_id: str, resolved: bool) -> None:
    _change(deck, lambda comments: _find(comments, comment_id).update(resolved=resolved))


def delete_comment(deck: Path, comment_id: str) -> None:
    def drop(comments: list[dict[str, Any]]) -> None:
        comments.remove(_find(comments, comment_id))

    _change(deck, drop)


def _store(deck: Path) -> Path:
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    return folder / COMMENTS


def _load(path: Path) -> list[dict[str, Any]]:
    """A store that is missing or not in the shape this module writes counts as no comments,
    so a damaged file never stops the deck from opening."""
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    comments = data.get("comments") if isinstance(data, dict) else None
    if not isinstance(comments, list):
        return []
    return [c for c in comments if isinstance(c, dict) and isinstance(c.get("id"), str)]


def _change(deck: Path, change: Any) -> None:
    path = _store(deck)
    with file_lock(path):
        comments = _load(path)
        change(comments)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps({"comments": comments}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        replace_with_retry(tmp, path)


def _find(comments: list[dict[str, Any]], comment_id: str) -> dict[str, Any]:
    for comment in comments:
        if comment["id"] == comment_id:
            return comment
    raise CommentNotFound(comment_id)


def _text(text: str) -> str:
    text = text.strip()
    if not text:
        raise ValueError("a comment needs some text")
    if len(text) > _MAX_TEXT:
        raise ValueError(f"a comment holds {_MAX_TEXT} characters at most")
    return text


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def move_comments(deck: Path, renamed: dict[str, str | None]) -> None:
    """Keeps comments on their slides when slides are renamed: `renamed` maps an old slide name to
    its new one, or to None for a slide that was deleted, whose comments go with it."""
    if not (pages_folder(deck) or Path()).joinpath(COMMENTS).is_file():
        return

    def follow(comments: list[dict[str, Any]]) -> None:
        kept = []
        for comment in comments:
            slide = comment.get("slide")
            if slide in renamed:
                if renamed[slide] is None:
                    continue
                comment["slide"] = renamed[slide]
            kept.append(comment)
        comments[:] = kept

    _change(deck, follow)
