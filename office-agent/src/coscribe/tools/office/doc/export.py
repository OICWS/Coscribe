"""A Doc written out as the markdown subset Word's writer takes, for the export to Word: what that
subset cannot hold is written as the nearest thing it can (decision 0025)."""

from __future__ import annotations

import re

from .blocks import Block, read_doc

_ALERT = re.compile(r"^>\s*\[!(\w+)\]\s*$")
_PICTURE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_FENCE = re.compile(r"^\s*(```|~~~)")


def _callout(text: str) -> str:
    head, *rest = text.splitlines()
    alert = _ALERT.match(head.strip())
    label = alert[1].capitalize() if alert else "Note"
    body = [re.sub(r"^\s{0,3}>\s?", "", line) for line in rest]
    first = next((i for i, line in enumerate(body) if line.strip()), None)
    if first is None:
        return f"**{label}**"
    body[first] = f"**{label}:** {body[first]}"
    return "\n".join(body)


def _chart(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip() and not _FENCE.match(line)]
    kind, _, title = (lines[0].strip() if lines else "").partition(" ")
    table = "\n".join(lines[1:])
    caption = f"**{title.strip() or kind.capitalize() + ' chart'}**"
    return f"{caption}\n\n{table}" if table else caption


def _block(block: Block) -> str | None:
    text = block.text
    if block.kind == "callout":
        return _callout(text)
    if block.kind == "chart":
        return _chart(text)
    if block.kind == "code":
        return "\n".join(line for line in text.splitlines() if not _FENCE.match(line))
    if block.kind == "quote":
        return "\n".join(re.sub(r"^\s{0,3}>\s?", "", line) for line in text.splitlines())
    if block.kind in ("html", "other"):
        return None
    return _PICTURE.sub(lambda m: f"[Picture: {m[1]}]" if m[1] else "[Picture]", text)


def docx_markdown(source: str) -> str:
    """The Doc's body as the subset `write_docx` takes: callouts as a bold label and their text, a
    chart as its title and its table, a picture as a bracketed note, html as nothing."""
    parts = [part for block in read_doc(source).blocks if (part := _block(block))]
    return "\n\n".join(parts) + "\n"
