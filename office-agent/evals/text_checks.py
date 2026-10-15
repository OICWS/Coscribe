"""Checks on the text of a produced file, the same for a deck, a workbook and a document."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from coscribe.tools.office.pptx.engine.checker import (
    is_claim,
    is_known,
    known_numbers,
    number_values,
)


def _fold(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", folded)


def normalise(text: str) -> str:
    """Fold full-width forms, thousands separators, spacing and case, so that `12,710`,
    `12710` and `１２，７１０` are one number and `Win + L` equals `win+l`."""
    return re.sub(r"\s+", "", _fold(text))


def contains(text: str, fact: str) -> bool:
    """A fact that starts or ends in a digit must not be part of a longer number: `3周` is not
    in `13周`, `42%` is not in `142%`, `120` is not in `1200`. Spacing inside the fact is free
    (`Win + L`), but the text keeps its spaces: `Q3 12,710` is not the number `312,710`."""
    needle = normalise(fact)
    if not needle:
        return False
    body = re.escape(needle[0])
    for previous, char in zip(needle, needle[1:], strict=False):
        body += ("" if previous.isdigit() and char.isdigit() else r"\s*") + re.escape(char)
    before = r"(?<![\d.])" if needle[0].isdigit() else ""
    after = r"(?!\d)" if needle[-1].isdigit() else ""
    return re.search(before + body + after, _fold(text)) is not None


def check_facts(text: str, facts: list[list[str]], absent: list[str]) -> dict[str, Any]:
    missing = [alts[0] for alts in facts if not any(contains(text, a) for a in alts)]
    still_there = [a for a in absent if contains(text, a)]
    return {
        "ok": not missing and not still_there,
        "found": len(facts) - len(missing),
        "total": len(facts),
        "missing": missing,
        "forbidden_present": still_there,
    }


def plain_number(value: float) -> str:
    """`12710000`, not `1.271e+07`: a fact is looked up as written."""
    return format(value, "f").rstrip("0").rstrip(".") if value % 1 else str(int(value))


def find_inventions(
    units: list[str], source_texts: list[str], allowed: list[str], unit: str
) -> dict[str, Any]:
    """Numbers in the text of a unit (a slide, a sheet, a section) that appear in no input. A
    derived figure (a sum, a percentage the model computed) is listed too: the list is for a
    person to read, not a failure."""
    known = known_numbers("\n".join([*source_texts, *allowed]))
    found: dict[str, list[int]] = {}
    for position, text in enumerate(units, start=1):
        for number, value in number_values(text):
            if is_claim(number) and not is_known(number, value, known):
                found.setdefault(number, []).append(position)
    return {
        "count": len(found),
        "numbers": [{"number": n, unit: s} for n, s in sorted(found.items())],
    }
