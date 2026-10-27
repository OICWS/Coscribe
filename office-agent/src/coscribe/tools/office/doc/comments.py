"""Comments on a Doc (decision 0025, as a deck's are, decision 0015): kept in `comments.json` in the
Doc's side folder, so they travel with it and outlive the app. A comment is anchored to the text of
the block it was made on, not to its number: coscribe or the person can insert or remove blocks, and
the comment follows its block, or is shown as detached when that text is gone."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..._file_locks import file_lock, replace_with_retry
from .blocks import read_doc
from .files import side_folder

COMMENTS = "comments.json"
_MAX_TEXT = 4000


class DocCommentNotFound(KeyError):
    """No comment with that id on this Doc."""


class DocCommentRefused(ValueError):
    """A comment this module will not make. `code` says why (`no_block`, `empty` or `too_long`);
    the caller shows its own text for it, never this exception's."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def read_doc_comments(path: Path) -> list[dict[str, Any]]:
    """The Doc's comments, oldest first, each with the block it now sits on (`block`, None when
    its text is gone) and `detached`."""
    blocks = [b.text for b in read_doc(path.read_text(encoding="utf-8")).blocks]
    return [{**c, **_where(c.get("anchor"), blocks)} for c in _load(_store(path))]


def _where(anchor: Any, blocks: list[str]) -> dict[str, Any]:
    """Where the comment's block is now: the block with the same text that is the same copy of it
    (the second of two equal blocks stays the second), or the last copy when copies were removed."""
    text = anchor.get("text") if isinstance(anchor, dict) else None
    nth = anchor.get("nth") if isinstance(anchor, dict) else None
    same = [i for i, block in enumerate(blocks) if block == text] if isinstance(text, str) else []
    if not same:
        return {"block": None, "detached": True}
    return {
        "block": same[min(nth if isinstance(nth, int) else 0, len(same) - 1)],
        "detached": False,
    }


def add_doc_comment(
    path: Path, *, block: int, text: str, author: str, sent: bool
) -> dict[str, Any]:
    """A new comment on block `block` of the Doc. `sent` says it went to coscribe as a message.
    `DocCommentRefused` (a code, not a text) for a block that does not exist or an empty or too
    long text."""
    blocks = read_doc(path.read_text(encoding="utf-8")).blocks
    if not 0 <= block < len(blocks):
        raise DocCommentRefused("no_block")
    comment = {
        "id": uuid.uuid4().hex[:12],
        "anchor": {
            "text": blocks[block].text,
            "nth": sum(b.text == blocks[block].text for b in blocks[:block]),
        },
        "text": _text(text),
        "author": author[:80],
        "created": _now(),
        "sent": sent,
        "resolved": False,
        "replies": [],
    }
    _change(path, lambda comments: comments.append(comment))
    return comment


def reply_to_doc_comment(path: Path, comment_id: str, *, text: str, author: str) -> dict[str, Any]:
    reply = {"author": author[:80], "text": _text(text), "created": _now()}
    _change(path, lambda comments: _find(comments, comment_id)["replies"].append(reply))
    return reply


def resolve_doc_comment(path: Path, comment_id: str, resolved: bool) -> None:
    _change(path, lambda comments: _find(comments, comment_id).update(resolved=resolved))


def delete_doc_comment(path: Path, comment_id: str) -> None:
    def drop(comments: list[dict[str, Any]]) -> None:
        comments.remove(_find(comments, comment_id))

    _change(path, drop)


def _store(path: Path) -> Path:
    return side_folder(path) / COMMENTS


def _load(store: Path) -> list[dict[str, Any]]:
    """A store that is missing or not in the shape this module writes counts as no comments, so a
    damaged file never stops the Doc from opening."""
    try:
        data: Any = json.loads(store.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    comments = data.get("comments") if isinstance(data, dict) else None
    if not isinstance(comments, list):
        return []
    return [c for c in comments if isinstance(c, dict) and isinstance(c.get("id"), str)]


def _change(path: Path, change: Any) -> None:
    store = _store(path)
    store.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(store):
        comments = _load(store)
        change(comments)
        tmp = store.with_name(f".{store.name}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps({"comments": comments}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        replace_with_retry(tmp, store)


def _find(comments: list[dict[str, Any]], comment_id: str) -> dict[str, Any]:
    for comment in comments:
        if comment["id"] == comment_id:
            return comment
    raise DocCommentNotFound(comment_id)


def _text(text: str) -> str:
    text = text.strip()
    if not text:
        raise DocCommentRefused("empty")
    if len(text) > _MAX_TEXT:
        raise DocCommentRefused("too_long")
    return text


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
