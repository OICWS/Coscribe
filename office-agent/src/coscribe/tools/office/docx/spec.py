"""The spec a Word document is written from (decision 0024): the markdown subset with an optional
YAML head and `:::` component blocks. It names what the document says and which component shows
it, never how it looks: there is no colour, font, size or spacing in it, so the theme alone decides
the look. A content without a head or a component is plain markdown, written as before."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

HEAD_KEYS = (
    "title",
    "subtitle",
    "author",
    "date",
    "cover",
    "toc",
    "header",
    "footer",
    "facts",
    "design_system",
)
COVER_STYLES = ("band", "rule", "none")
COMPONENTS = ("stats", "callout", "chart", "figure", "pagebreak")
CALLOUT_KINDS = ("info", "success", "warn", "danger")

_FENCE_OPEN = re.compile(r"^:::\s*([a-z]+)\s*(.*)$")
_FENCE_CLOSE = re.compile(r"^:::\s*$")
_FACT = re.compile(r"\{fact:([A-Za-z0-9_]+)\}")


class SpecError(ValueError):
    """The spec is not one the compiler can write; the text says what to change."""


@dataclass
class Component:
    name: str
    args: str
    body: str


@dataclass
class Spec:
    head: dict[str, Any] = field(default_factory=dict)
    # Markdown text (str) and components, in the order they are written.
    items: list[str | Component] = field(default_factory=list)

    @property
    def is_plain(self) -> bool:
        """No head and no component: plain markdown, written as `write_docx` always wrote it."""
        return not self.head and all(isinstance(item, str) for item in self.items)


def _split_head(content: str) -> tuple[dict[str, Any], str]:
    lines = content.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        raise SpecError("The document head starts with --- and has no closing ---")
    import yaml

    try:
        head = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as error:
        raise SpecError(f"The document head is not valid YAML: {error}") from None
    if not isinstance(head, dict):
        raise SpecError("The document head is a list of `key: value` lines")
    return head, "\n".join(lines[end + 1 :])


def _check_head(head: dict[str, Any]) -> None:
    unknown = [key for key in head if key not in HEAD_KEYS]
    if unknown:
        raise SpecError(
            f"Unknown document head key {unknown[0]!r}. The head has: {', '.join(HEAD_KEYS)}. "
            "Colours, fonts and sizes are not set in the document; the design system sets them."
        )
    if "cover" in head and head["cover"] not in COVER_STYLES:
        raise SpecError(f"cover is one of: {', '.join(COVER_STYLES)}")
    facts = head.get("facts", {})
    if not isinstance(facts, dict) or not all(
        re.fullmatch(r"[A-Za-z0-9_]+", str(name)) for name in facts
    ):
        raise SpecError("facts is a list of `name: value` lines; a name has letters, digits and _")


def _components(text: str) -> list[str | Component]:
    items: list[str | Component] = []
    plain: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        opened = _FENCE_OPEN.match(lines[index].strip())
        if opened is None:
            plain.append(lines[index])
            index += 1
            continue
        name, args = opened.group(1), opened.group(2).strip()
        if name not in COMPONENTS:
            raise SpecError(f"Unknown component {name!r}. Components: {', '.join(COMPONENTS)}")
        body: list[str] = []
        index += 1
        while index < len(lines) and not _FENCE_CLOSE.match(lines[index].strip()):
            body.append(lines[index])
            index += 1
        if index >= len(lines):
            raise SpecError(f"The {name} component has no closing :::")
        index += 1
        if plain:
            items.append("\n".join(plain))
            plain = []
        items.append(Component(name, args, "\n".join(body).strip()))
    if plain:
        items.append("\n".join(plain))
    return items


def expand_facts(text: str, facts: dict[str, Any]) -> str:
    """`{fact:name}` replaced by the value the head gives it; an undefined name is an error."""

    def value(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in facts:
            known = ", ".join(sorted(map(str, facts))) or "none"
            raise SpecError(
                f"{{fact:{name}}} is not defined in the head's facts (defined: {known})"
            )
        return str(facts[name])

    return _FACT.sub(value, text)


def parse_spec(content: str) -> Spec:
    head, rest = _split_head(content)
    _check_head(head)
    facts = {str(name): value for name, value in head.get("facts", {}).items()}
    items = _components(expand_facts(rest, facts))
    for item in items:
        if isinstance(item, Component) and item.name == "callout":
            kind = item.args.split(" ", 1)[0] or "info"
            if kind not in CALLOUT_KINDS:
                raise SpecError(f"A callout is one of: {', '.join(CALLOUT_KINDS)}")
    head = {
        key: expand_facts(value, facts) if isinstance(value, str) else value
        for key, value in head.items()
    }
    return Spec(head=head, items=items)
