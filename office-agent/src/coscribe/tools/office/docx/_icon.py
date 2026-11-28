"""The picture Word shows for a file embedded as an icon: a page with a badge for the file's
kind and the file's name beneath it, drawn as an EMF so it stays sharp when printed or zoomed,
and so the name is real text a reader of the document can find, not pixels."""

from __future__ import annotations

import struct
from pathlib import PurePath

_DPI = 96
_WIDTH = 114
_ICON = 58
_LINE = 14
_MAX_LINE = 108
# Badge colour and letter per kind; anything else gets a plain grey page.
_KINDS = {
    ".pptx": (0x1C3EC4, "P"),
    ".ppt": (0x1C3EC4, "P"),
    ".xlsx": (0x417C10, "X"),
    ".xls": (0x417C10, "X"),
    ".docx": (0xBD5A18, "W"),
    ".doc": (0xBD5A18, "W"),
    ".pdf": (0x0F0FB4, "PDF"),
}
_GREY = 0x7F7F7F


def _record(kind: int, body: bytes) -> bytes:
    return struct.pack("<II", kind, 8 + len(body)) + body


def _rect(left: int, top: int, right: int, bottom: int) -> bytes:
    return struct.pack("<4i", left, top, right, bottom)


def _brush(slot: int, colour: int) -> bytes:
    return _record(39, struct.pack("<IIII", slot, 0, colour, 0))


def _pen(slot: int, colour: int) -> bytes:
    return _record(38, struct.pack("<IIiiI", slot, 0, 1, 0, colour))


def _select(slot: int) -> bytes:
    return _record(37, struct.pack("<I", slot))


def _delete(slot: int) -> bytes:
    return _record(40, struct.pack("<I", slot))


def _polygon(points: list[tuple[int, int]]) -> bytes:
    xs, ys = [x for x, _ in points], [y for _, y in points]
    body = _rect(min(xs), min(ys), max(xs), max(ys)) + struct.pack("<I", len(points))
    body += b"".join(struct.pack("<hh", x, y) for x, y in points)
    return _record(86, body)


def _font(slot: int, height: int, bold: bool, face: str) -> bytes:
    logfont = struct.pack(
        "<iiiii8B64s",
        -height,
        0,
        0,
        0,
        700 if bold else 400,
        0,
        0,
        0,
        1,  # DEFAULT_CHARSET: the font mapper picks one that has the characters
        0,
        0,
        5,  # CLEARTYPE_QUALITY
        0,
        face.encode("utf-16-le")[:62],
    )
    return _record(82, struct.pack("<I", slot) + logfont)


def _text(x: int, y: int, text: str, advance: list[int]) -> bytes:
    """One centred line (EMR_EXTTEXTOUTW): the string, then each character's advance."""
    chars = text.encode("utf-16-le")
    chars += b"\0" * (-len(chars) % 4)
    string_at = 8 + 16 + 12 + 40
    dx_at = string_at + len(chars)
    emrtext = struct.pack("<iiIII", x, y, len(text), string_at, 0) + _rect(0, 0, -1, -1)
    emrtext += struct.pack("<I", dx_at)
    width = sum(advance)
    bounds = _rect(x - width // 2, y, x + width // 2, y + _LINE)
    body = bounds + struct.pack("<Iff", 1, 0.0, 0.0) + emrtext + chars
    body += b"".join(struct.pack("<i", a) for a in advance)
    return _record(84, body)


def _advance(char: str, height: int) -> int:
    """Roughly how far a character moves the pen: readers place each one by these numbers."""
    if ord(char) > 0x2E7F:
        return height
    if char in "il.,:;'|!jtfr ()[]":
        return round(height * 0.32)
    if char in "mwMW@%":
        return round(height * 0.85)
    return round(height * (0.66 if char.isupper() else 0.55))


def _lines(name: str, height: int) -> list[str]:
    """The name broken the way Word breaks an icon's label: as many characters as fit a line,
    at most three lines, the last cut short with an ellipsis."""
    lines, current, width = [], "", 0
    for char in name:
        step = _advance(char, height)
        if current and width + step > _MAX_LINE:
            lines.append(current)
            current, width = "", 0
        current += char
        width += step
    lines.append(current)
    if len(lines) > 3:
        lines = [*lines[:2], lines[2][:-1] + "…"]
    return lines


def icon_emf(name: str) -> tuple[bytes, float, float]:
    """The icon for a file named `name`, as EMF bytes and its width and height in points."""
    colour, letter = _KINDS.get(PurePath(name).suffix.lower(), (_GREY, ""))
    caption_height = 12
    lines = _lines(name, caption_height)
    height = _ICON + _LINE * len(lines) + 4
    face = "Microsoft YaHei" if any(ord(c) > 0x2E7F for c in name) else "Segoe UI"

    body = [
        _record(18, struct.pack("<I", 1)),  # transparent text background
        _pen(1, _GREY),
        _brush(2, 0xFFFFFF),
        _select(1),
        _select(2),
        _polygon([(42, 4), (72, 4), (82, 14), (82, 54), (42, 54)]),
        _brush(3, 0xE6E6E6),
        _select(3),
        _polygon([(72, 4), (72, 14), (82, 14)]),
        _brush(4, colour),
        _pen(5, colour),
        _select(4),
        _select(5),
        _polygon([(30, 18), (60, 18), (60, 44), (30, 44)]),
    ]
    if letter:
        letter_height = 18 if len(letter) == 1 else 11
        body += [
            _font(6, letter_height, True, "Segoe UI"),
            _select(6),
            _record(24, struct.pack("<I", 0xFFFFFF)),
            _record(22, struct.pack("<I", 6)),  # TA_CENTER | TA_TOP
            _text(
                45,
                31 - letter_height // 2 - 1,
                letter,
                [_advance(c, letter_height) for c in letter],
            ),
        ]
    body += [
        _font(7, caption_height, False, face),
        _select(7),
        _record(24, struct.pack("<I", 0)),
        _record(22, struct.pack("<I", 6)),
    ]
    for i, line in enumerate(lines):
        advance = [_advance(c, caption_height) for c in line]
        body.append(_text(_WIDTH // 2, _ICON + _LINE * i, line, advance))
    body += [_delete(slot) for slot in range(1, 8)]
    records = b"".join(body) + _record(14, struct.pack("<III", 0, 16, 20))

    per_mm = _DPI / 25.4
    frame = _rect(0, 0, round(_WIDTH / per_mm * 100), round(height / per_mm * 100))
    header_body = (
        _rect(0, 0, _WIDTH - 1, height - 1)
        + frame
        + struct.pack("<II", 0x464D4520, 0x10000)
        + struct.pack("<IIHH", 0, 0, 8, 0)
        + struct.pack("<III", 0, 0, 0)
        + struct.pack("<ii", 1920, 1080)
        + struct.pack("<ii", round(1920 / per_mm), round(1080 / per_mm))
    )
    header = _record(1, header_body)
    count = 1 + _count(records)
    header = header[:48] + struct.pack("<II", len(header) + len(records), count) + header[56:]
    return header + records, _WIDTH * 72 / _DPI, height * 72 / _DPI


def _count(records: bytes) -> int:
    count, pos = 0, 0
    while pos < len(records):
        pos += struct.unpack_from("<I", records, pos + 4)[0]
        count += 1
    return count
