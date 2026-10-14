"""How wide a cell's shown text is, measured the way Excel draws it."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any

# Excel's and LibreOffice's width of a column nobody sized, in characters of the default font.
DEFAULT_WIDTH = 8.43
# The cell's own margins and a bold header eat about two characters of the width.
PADDING = 2.0
# One long note must not push the rest of the sheet off the page; past this the text is cut,
# which a reader can still widen, rather than every other column being scrolled away.
MAX_WIDTH = 50.0
# Excel shows a General number in at most this many characters, rounding decimals or switching
# to scientific notation rather than printing `###`.
_GENERAL_MAX_CHARS = 11
_DIGIT_CODES = "0#?"
# Fractions, dates, times and text placeholders are not rendered here; such a format is measured
# by its own length or the General text, whichever is longer.
_UNMEASURED_CODES = frozenset("/@yYmMdDhHsS")


def text_width(text: str) -> float:
    """Width in characters of the default font; a CJK or full-width character takes two."""
    widest = 0
    for line in text.split("\n"):
        widest = max(widest, sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in line))
    return float(widest)


def _sections(number_format: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    quoted = escaped = False
    for char in number_format:
        if escaped:
            escaped = False
        elif char == "\\" and not quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char == ";" and not quoted:
            sections.append("".join(current))
            current = []
            continue
        current.append(char)
    sections.append("".join(current))
    return sections


@dataclass
class _Section:
    codes: list[str] = field(default_factory=list)
    prefix: list[str] = field(default_factory=list)
    suffix: list[str] = field(default_factory=list)
    exponent: bool = False
    unmeasured: bool = False

    def literal(self, text: str) -> None:
        (self.suffix if self.codes else self.prefix).append(text)


def _closing(section: str, start: int, mark: str) -> int:
    end = section.find(mark, start)
    return len(section) if end < 0 else end


def _parse(section: str) -> _Section:
    """The digit codes (`#,##0.00%`) and the text printed before and after them (`$`, `元`)."""
    parsed = _Section()
    i = 0
    while i < len(section):
        char, following = section[i], section[i + 1 : i + 2]
        if char == '"':
            end = _closing(section, i + 1, '"')
            parsed.literal(section[i + 1 : end])
            i = end + 1
            continue
        if char == "[":
            end = _closing(section, i, "]")
            if section[i + 1 : i + 2] == "$":
                parsed.literal(section[i + 2 : end].split("-")[0])
            i = end + 1
            continue
        if char in "Ee" and following in "+-" and following and parsed.codes:
            parsed.exponent = True
            break
        if char in "\\_*":
            # `\x` prints x, `_x` leaves a gap as wide as x, `*x` only fills spare room.
            parsed.literal("" if char == "*" else following)
            i += 2
            continue
        if char in _DIGIT_CODES + ".,%":
            parsed.codes.append(char)
        else:
            parsed.unmeasured = parsed.unmeasured or char in _UNMEASURED_CODES
            parsed.literal(char)
        i += 1
    return parsed


def _general(value: float) -> str:
    text = str(value) if isinstance(value, int) else f"{value:.15g}"
    return text[:_GENERAL_MAX_CHARS]


def _pick_section(value: float, sections: list[str]) -> str:
    if value < 0 and len(sections) > 1:
        return sections[1]
    if value == 0 and len(sections) > 2:
        return sections[2]
    return sections[0]


def _number(value: float, parsed: _Section) -> str:
    codes = "".join(parsed.codes)
    integer_codes, _, decimal_codes = codes.replace("%", "").partition(".")
    decimals = sum(decimal_codes.count(code) for code in _DIGIT_CODES)
    if parsed.exponent:
        return f"{abs(value):.{decimals}E}"
    percent = codes.count("%")
    # A comma after the last digit divides by a thousand (`#,##0,"K"`).
    thousands = len(integer_codes) - len(integer_codes.rstrip(","))
    shown = abs(value) * 100**percent / 1000**thousands
    grouping = "," if "," in integer_codes.rstrip(",") else ""
    return f"{shown:{grouping}.{decimals}f}{'%' * percent}"


def _formatted(value: float, number_format: str) -> str:
    sections = _sections(number_format)
    section = _pick_section(value, sections)
    if section.strip().lower() in ("general", ""):
        return _general(value)
    parsed = _parse(section)
    if parsed.unmeasured:
        return max(_general(value), section.replace('"', ""), key=text_width)
    sign = "-" if value < 0 and len(sections) == 1 else ""
    prefix, suffix = "".join(parsed.prefix), "".join(parsed.suffix)
    if not any(code in parsed.codes for code in _DIGIT_CODES):
        return sign + prefix + suffix
    return f"{sign}{prefix}{_number(value, parsed)}{suffix}"


def displayed_text(value: Any, number_format: str = "General") -> str:
    """The text a cell shows: a number with its number format applied."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        return _formatted(value, number_format or "General")
    return str(value)


def needed_width(value: Any, number_format: str = "General") -> float:
    """The column width that shows the value whole; 0 for an empty cell."""
    width = text_width(displayed_text(value, number_format))
    return width + PADDING if width else 0.0
