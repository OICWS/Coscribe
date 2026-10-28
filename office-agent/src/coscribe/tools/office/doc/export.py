"""A Doc written out as the markdown subset Word's writer takes, for the export to Word: what that
subset cannot hold is written as the nearest thing it can (decision 0025)."""

from __future__ import annotations

import re

from .blocks import Block, read_doc

_ALERT = re.compile(r"^>\s*\[!(\w+)\]\s*$")
_PICTURE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_FENCE = re.compile(r"^\s*(```|~~~)")
_TASK = re.compile(r"^(\s*(?:[-*+]|\d+[.)]))\s+\[([ xX])\]\s+", re.MULTILINE)


def _callout(text: str) -> str:
    head, *rest = text.splitlines()
    alert = _ALERT.match(head.strip())
    kind = alert[1].upper() if alert else "NOTE"
    body = [re.sub(r"^\s{0,3}>\s?", "", line) for line in rest]
    return f"§callout:{kind}:{kind.capitalize()}§\n\n" + "\n".join(body).strip() + "\n\n§/callout§"


def _chart(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip() and not _FENCE.match(line)]
    kind, _, title = (lines[0].strip() if lines else "").partition(" ")
    table = "\n".join(lines[1:])
    title = title.strip() or kind.capitalize() + " chart"
    # The writer turns the table that follows the marker into the chart's data.
    return f"§chart:{kind}:{title.replace('§', '')}§\n\n{table}" if table else f"**{title}**"


def _block(block: Block) -> str | None:
    text = block.text
    if block.kind == "callout":
        return _callout(text)
    if block.kind == "chart":
        return _chart(text)
    if block.kind == "rule":
        return "§rule§"
    if block.kind == "code":
        return "\n".join(line for line in text.splitlines() if not _FENCE.match(line))
    if block.kind == "quote":
        return "\n".join(re.sub(r"^\s{0,3}>\s?", "", line) for line in text.splitlines())
    if block.kind in ("html", "other"):
        return None
    text = _PICTURE.sub(lambda m: f"[Picture: {m[1]}]" if m[1] else "[Picture]", text)
    return _TASK.sub(lambda m: f"{m[1]} {'☐' if m[2] == ' ' else '☑'} ", text)


def docx_markdown(source: str) -> str:
    """The Doc's body as the subset `write_docx` takes, with marker paragraphs for what the subset
    cannot say: a callout framed in its colour, a chart drawn natively from its table, a task item
    with its box. A picture is a bracketed note, html nothing."""
    parts = [part for block in read_doc(source).blocks if (part := _block(block))]
    return "\n\n".join(parts) + "\n"
