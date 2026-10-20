"""Check that what the Slides panel offers reaches the exported .pptx.

A deck is built from section pages through `build_deck`; the XML of the file is then read and the
check fails when a property the panel writes is missing from it. The unit tests assert the same
keys one at a time on the Linux job; this script runs the whole deck as one file on a Windows
runner (paths, line endings and the temp folder differ there). Run it from `office-agent/`:

    python scripts/check_deck_export.py        # a table of results; exit 1 if a check fails

It works in a fresh temporary folder (`--out DIR` keeps the deck).
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import tempfile
import zipfile
import zlib
from collections.abc import Callable
from pathlib import Path

from pptx import Presentation

from coscribe.tools.office.pptx.engine import build_deck

BOX = "left:{x}px;top:{y}px;width:{w}px;height:{h}px"

TEXT = (
    '<p id="text" style="left:100px;top:60px;width:800px;height:120px;font-size:40px;'
    'font-weight:700;font-style:italic">Styled text</p>'
)
PICTURE = (
    '<img id="pic" src="a.png" style="left:100px;top:200px;width:400px;height:300px;'
    'border-radius:40px;border:6px solid #112233;opacity:0.5"/>'
)
# The engine refuses a shadow on a picture that is also rounded, so the shadow has its own.
SHADOWED = (
    '<img id="lit" src="a.png" style="left:1100px;top:200px;width:400px;height:300px;'
    'box-shadow:0px 8px 24px #112233 0.4"/>'
)
SHAPE = (
    '<x-shape id="shape" data-shape="round-rect" style="left:600px;top:200px;width:400px;'
    "height:300px;background:#ABCDEF;border-radius:30px;border:4px solid #334455;"
    'box-shadow:0px 6px 18px #000000"/>'
)
CHART = {
    "type": "column",
    "categories": ["A", "B", "C"],
    "series": [{"name": "S1", "values": [3, 5, 2]}, {"name": "S2", "values": [1, 4, 6]}],
    "title": "Revenue",
    "show_legend": True,
    "data_labels": True,
    "grouping": "stacked",
    "style": {"colors": ["#C2410C", "#0E3A66"]},
}
CHART_ELEMENT = (
    '<x-chart id="chart" style="left:100px;top:100px;width:900px;height:600px">'
    f"{json.dumps(CHART)}</x-chart>"
)
CARDS = (
    '<x-stack id="row" data-layout="row" style="left:100px;top:200px;width:1700px;height:400px;'
    'gap:40px;padding:30px;background:#F3F4F6;border-radius:16px">'
    + "".join(
        '<x-stack style="flex-grow:1;gap:12px;padding:20px;background:#FFFFFF">'
        f"<h3>Card {n}</h3><p>Body {n}</p></x-stack>"
        for n in (1, 2, 3)
    )
    + "</x-stack>"
)

PAGES = {
    "01-objects.html": f"<section>{TEXT}{PICTURE}{SHADOWED}{SHAPE}</section>",
    "02-chart.html": f"<section>{CHART_ELEMENT}</section>",
    "03-cards.html": f"<section>{CARDS}</section>",
}


def _png(path: Path) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = struct.pack(">I", len(data)) + kind + data
        return body + struct.pack(">I", zlib.crc32(kind + data))

    rows = b"".join(b"\x00" + bytes([200, 30, 30]) * 40 for _ in range(30))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 40, 30, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def build(folder: Path) -> Path:
    pages = folder / "pages"
    pages.mkdir()
    _png(pages / "a.png")
    for name, source in PAGES.items():
        (pages / name).write_text(source, encoding="utf-8")
    out = folder / "deck.pptx"
    report = build_deck(pages, out, resource_root=folder)
    if not report.ok:
        errors = [e for page in report.pages for e in page.errors]
        raise SystemExit(f"the deck did not build: {errors}")
    return out


def _find(xml: str, pattern: str) -> str:
    found = re.search(pattern, xml, re.S)
    if found is None:
        raise AssertionError(f"not in the file: {pattern}")
    return found[0]


def _has(part: str, *needles: str) -> None:
    for needle in needles:
        if needle not in part:
            raise AssertionError(f"missing {needle!r}")


def check_text(slides: list[str], _charts: list[str]) -> None:
    run = _find(slides[0], r"<a:r>(?:(?!</a:r>).)*Styled text.*?</a:r>")
    # A slide is 1920px across 960pt, so 40px is 20pt.
    _has(run, 'sz="2000"', 'b="1"', 'i="1"')


def check_picture(slides: list[str], _charts: list[str]) -> None:
    rounded, lit = re.findall(r"<p:pic>.*?</p:pic>", slides[0], re.S)
    # 40px of a 300px side is 13333 of 100000; 6px is 38100 EMU; opacity 0.5 is 50000.
    _has(
        rounded, 'prst="roundRect"', 'fmla="val 13333"', '<a:ln w="38100">', 'srgbClr val="112233"'
    )
    _has(rounded, '<a:alphaModFix amt="50000"/>')
    _has(_find(lit, r"<a:outerShdw.*?</a:outerShdw>"), 'blurRad="152400"', 'dist="50800"')


def check_shape(slides: list[str], _charts: list[str]) -> None:
    shape = _find(slides[0], r"<p:sp>(?:(?!</p:sp>).)*ABCDEF.*?</p:sp>")
    _has(shape, 'prst="roundRect"', 'srgbClr val="ABCDEF"', "<a:ln", 'srgbClr val="334455"')
    _has(shape, "<a:outerShdw")


def check_chart(_slides: list[str], charts: list[str]) -> None:
    if len(charts) != 1:
        raise AssertionError(f"{len(charts)} charts in the file, expected 1")
    _has(
        charts[0],
        "<c:legend>",
        "<c:dLbls>",
        "Revenue",
        '<c:grouping val="stacked"',
        'srgbClr val="C2410C"',
        'srgbClr val="0E3A66"',
    )


def check_cards(slides: list[str], _charts: list[str]) -> None:
    xml = slides[2]
    for n in (1, 2, 3):
        _has(xml, f"Card {n}", f"Body {n}")
    # The row and each card are laid out into plain shapes: nothing of the container is left.
    if re.search(r"x-stack|data-layout|flex-grow", xml):
        raise AssertionError("a container is left in the file")
    if xml.count("<p:sp>") < 4:
        raise AssertionError("the row and its cards did not become shapes")


CHECKS: tuple[tuple[str, Callable[[list[str], list[str]], None]], ...] = (
    ("text: size and style", check_text),
    ("picture: radius, border, opacity, shadow", check_picture),
    ("shape: fill, radius, border, shadow", check_shape),
    ("chart: title, legend, labels, colours, stacked", check_chart),
    ("container: cards become plain shapes", check_cards),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--out", type=Path, help="build the deck in this existing folder, and keep it"
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as scratch:
        deck = build(args.out or Path(scratch))
        count = len(Presentation(str(deck)).slides)  # the file opens with python-pptx
        with zipfile.ZipFile(deck) as pptx:
            names = pptx.namelist()
            numbered = sorted(
                (n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                key=lambda n: int(re.findall(r"\d+", n)[0]),
            )
            slides = [pptx.read(n).decode() for n in numbered]
            charts = [
                pptx.read(n).decode() for n in names if re.fullmatch(r"ppt/charts/chart\d*\.xml", n)
            ]

    results: list[tuple[str, str | None]] = [
        ("slide count", None if count == len(PAGES) else f"{count} slides, expected {len(PAGES)}")
    ]
    for case, check in CHECKS:
        try:
            check(slides, charts)
            results.append((case, None))
        except AssertionError as error:
            results.append((case, str(error)))
    for case, problem in results:
        print(f"{'FAIL' if problem else 'ok  '}  {case}" + (f"  ({problem})" if problem else ""))
    failed = sum(problem is not None for _, problem in results)
    print(f"{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
