"""A file wrapped as an OLE Package object, the form Word gives any file inserted "from file,
display as icon": a compound file whose `Ole10Native` stream holds the file's name and bytes.
Double-clicking the icon in Word opens the file in the program that owns its type, so one form
serves a deck, a workbook, a PDF or anything else, and the bytes travel inside the document."""

from __future__ import annotations

import math
import struct

_SECTOR = 512
_MINI = 64
_CUTOFF = 4096
_FREE, _END, _FAT, _DIF = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC
_IDS_PER_SECTOR = _SECTOR // 4
_HEADER_DIFAT = 109
# {0003000C-0000-0000-C000-000000000046}, the class of the Windows packager.
_PACKAGE_CLSID = bytes.fromhex("0c00030000000000c000000000000046")


def _ansi(text: str) -> bytes:
    return text.encode("ascii", "replace") + b"\0"


def _unicode(text: str) -> bytes:
    return struct.pack("<I", len(text)) + text.encode("utf-16-le")


def _native(name: str, data: bytes) -> bytes:
    """The packager's record: the label and paths in the old ANSI form, the bytes, then the
    same three strings in UTF-16, which is what Windows reads for a name outside ASCII."""
    temp = f"C:\\Temp\\{name}"
    body = b"".join(
        (
            struct.pack("<H", 2),
            _ansi(name),
            _ansi(name),
            struct.pack("<HH", 0, 3),
            struct.pack("<I", len(_ansi(temp))),
            _ansi(temp),
            struct.pack("<I", len(data)),
            data,
            _unicode(temp),
            _unicode(name),
            _unicode(name),
        )
    )
    return struct.pack("<I", len(body)) + body


def _comp_obj() -> bytes:
    def counted(text: str) -> bytes:
        raw = text.encode("ascii") + b"\0"
        return struct.pack("<I", len(raw)) + raw

    return b"".join(
        (
            bytes.fromhex("0100feff030a0000ffffffff"),
            _PACKAGE_CLSID,
            counted("OLE Package"),
            struct.pack("<I", 0),
            counted("Package"),
            struct.pack("<IIII", 0x71B239F4, 0, 0, 0),
        )
    )


def _ordered(names: list[str]) -> list[str]:
    """Compound-file order for siblings: shorter names first, then by upper case."""
    return sorted(names, key=lambda n: (len(n), n.upper()))


def _tree(ids: list[int]) -> tuple[int, dict[int, tuple[int, int]]]:
    """A balanced binary tree over `ids` (already in order): its root and each id's (left,
    right). Balanced, every node can be black and the red-black rules still hold."""
    links: dict[int, tuple[int, int]] = {}

    def build(lo: int, hi: int) -> int:
        if lo >= hi:
            return _FREE
        mid = (lo + hi) // 2
        links[ids[mid]] = (build(lo, mid), build(mid + 1, hi))
        return ids[mid]

    return build(0, len(ids)), links


def _entry(
    name: str, kind: int, left: int, right: int, child: int, start: int, size: int, clsid: bytes
) -> bytes:
    encoded = (name.encode("utf-16-le") + b"\0\0") if name else b""
    return struct.pack(
        "<64sHBBIII16sIQQIQ",
        encoded,
        len(encoded),
        kind,
        1,
        left,
        right,
        child,
        clsid,
        0,
        0,
        0,
        start,
        size,
    )


def _padded(data: bytes, unit: int) -> bytes:
    return data + b"\0" * (-len(data) % unit)


def _ids(values: list[int]) -> bytes:
    return b"".join(struct.pack("<I", v) for v in values)


def _mini_stream(
    streams: dict[str, bytes], small: list[str]
) -> tuple[bytes, bytes, dict[str, int]]:
    """The small streams packed in 64-byte pieces, their allocation table, and where each starts."""
    mini, table, starts = b"", [], {}
    for name in small:
        data = _padded(streams[name], _MINI)
        count = len(data) // _MINI
        first = len(mini) // _MINI
        starts[name] = first if count else _END
        table += [first + i + 1 for i in range(count - 1)] + ([_END] if count else [])
        mini += data
    return _padded(mini, _SECTOR), _padded(_ids(table), _SECTOR), starts


def _table_counts(data_sectors: int) -> tuple[int, int]:
    """How many allocation (FAT) and extension (DIFAT) sectors a file of `data_sectors` needs;
    they count themselves, so settle the two numbers together."""
    fat = difat = 0
    while True:
        total = data_sectors + fat + difat
        need_fat = math.ceil(total / _IDS_PER_SECTOR)
        need_difat = math.ceil(max(0, need_fat - _HEADER_DIFAT) / (_IDS_PER_SECTOR - 1))
        if (need_fat, need_difat) == (fat, difat):
            return fat, difat
        fat, difat = need_fat, need_difat


def compound_file(streams: dict[str, bytes], clsid: bytes = b"\0" * 16) -> bytes:
    """A version 3 compound file holding `streams` under its root. The tables come first and
    the large streams last, as Word lays them out: a large stream's bytes then run unbroken to
    near the end, where a reader that looks for a zip at the end of the file still finds it."""
    names = _ordered(list(streams))
    big = [n for n in names if len(streams[n]) >= _CUTOFF]
    small = [n for n in names if len(streams[n]) < _CUTOFF]
    mini, mini_table, starts = _mini_stream(streams, small)
    entry_count = 1 + len(names)
    dir_count = math.ceil(entry_count / 4)
    blobs = [_padded(streams[n], _SECTOR) for n in big]
    data_sectors = dir_count + (len(mini) + len(mini_table) + sum(map(len, blobs))) // _SECTOR
    fat_count, difat_count = _table_counts(data_sectors)

    chains: list[tuple[int, int]] = []
    sector = fat_count + difat_count

    def place(count: int) -> int:
        nonlocal sector
        first = sector
        if count:
            chains.append((first, count))
        sector += count
        return first if count else _END

    dir_start = place(dir_count)
    mini_fat_count = len(mini_table) // _SECTOR
    mini_fat_start = place(mini_fat_count)
    mini_start = place(len(mini) // _SECTOR)
    for name, blob in zip(big, blobs, strict=True):
        starts[name] = place(len(blob) // _SECTOR)

    ids = {name: i + 1 for i, name in enumerate(names)}
    root_child, links = _tree([ids[n] for n in names])
    entries = [_entry("Root Entry", 5, _FREE, _FREE, root_child, mini_start, len(mini), clsid)]
    for name in names:
        left, right = links[ids[name]]
        size = len(streams[name])
        entries.append(_entry(name, 2, left, right, _FREE, starts[name], size, b"\0" * 16))
    entries.append(_empty_entries(dir_count * 4 - entry_count))

    fat = [_FREE] * (fat_count * _IDS_PER_SECTOR)
    for first, count in chains:
        for i in range(count):
            fat[first + i] = first + i + 1 if i < count - 1 else _END
    fat_sectors = list(range(fat_count))
    difat_sectors = list(range(fat_count, fat_count + difat_count))
    for s in fat_sectors:
        fat[s] = _FAT
    for s in difat_sectors:
        fat[s] = _DIF
    difat = b""
    rest = fat_sectors[_HEADER_DIFAT:]
    step = _IDS_PER_SECTOR - 1
    for i in range(difat_count):
        part = rest[i * step : (i + 1) * step]
        nxt = difat_sectors[i + 1] if i + 1 < difat_count else _END
        difat += _ids([*part, *[_FREE] * (step - len(part)), nxt])

    head = fat_sectors[:_HEADER_DIFAT]
    header = struct.pack(
        "<8s16sHHHHH6sIIIIIIIII",
        bytes.fromhex("d0cf11e0a1b11ae1"),
        b"\0" * 16,
        0x3E,
        3,
        0xFFFE,
        9,
        6,
        b"\0" * 6,
        0,
        fat_count,
        dir_start,
        0,
        _CUTOFF,
        mini_fat_start,
        mini_fat_count,
        difat_sectors[0] if difat_sectors else _END,
        difat_count,
    ) + _ids(head + [_FREE] * (_HEADER_DIFAT - len(head)))
    return b"".join((header, _ids(fat), difat, *entries, mini_table, mini, *blobs))


def _empty_entries(count: int) -> bytes:
    return b"".join(_entry("", 0, _FREE, _FREE, _FREE, 0, 0, b"\0" * 16) for _ in range(count))


def ole_package(name: str, data: bytes) -> bytes:
    """`data` as the OLE Package object Word embeds for a file named `name`."""
    return compound_file(
        {
            "\x01CompObj": _comp_obj(),
            "\x01Ole": bytes.fromhex("0100000200000000") + b"\0" * 12,
            "\x01Ole10Native": _native(name, data),
        },
        clsid=_PACKAGE_CLSID,
    )
