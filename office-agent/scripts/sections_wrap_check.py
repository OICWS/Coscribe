"""Write a deck that shows whether PowerPoint breaks section text where the compiler expects.

Each paragraph sits in a tinted box exactly as tall as the compiler's line breaking says it needs.
Opened in PowerPoint on Windows, text that runs below its box (or a box with an empty last line)
is a paragraph PowerPoint wraps differently from `text_layout`, which the overflow check relies
on. Only PowerPoint itself can answer that, so this is run by hand:

    python scripts/sections_wrap_check.py wrap-check.pptx
"""

from __future__ import annotations

import sys
from pathlib import Path

from coscribe.tools.office.pptx.engine import compile_sections
from coscribe.tools.office.pptx.engine.section_format import parse_section, text_element
from coscribe.tools.office.pptx.engine.text_layout import text_height

_TEXTS = [
    "收入同比增长 23.5%，达到 5,410 万元，主要来自华东区新客户和续约率的提升。",
    "Revenue grew 23.5% to 54.1 million, mostly from new customers in the east region.",
    "华东区 Q3 新签客户 42 家（其中 KA 客户 7 家），占新增收入的一半以上；续约率 91%。",
    "A long sentence without much punctuation keeps going so that it has to wrap several "
    "times across the box, which is where small width differences add up line by line.",
]
_WIDTHS = (420, 640, 900)
_SIZES = (24, 32)


def _section(index: int, size: int, width: int) -> str:
    boxes = []
    for row, text in enumerate(_TEXTS):
        style = f"left:96px;top:0px;width:{width}px;height:1px;font-size:{size}px"
        probe = parse_section(f'<section><p style="{style}">{text}</p></section>')
        element = text_element(*probe.elements[0], probe)
        height = text_height(element.paragraphs, width, element.line_height)
        top = 140 + row * 230
        boxes.append(
            f'<p style="left:96px;top:{top}px;width:{width}px;height:{height:.1f}px;'
            f'font-size:{size}px;background:#E0F2FE">{text}</p>'
        )
    label = f"{size} px text, {width} px boxes"
    title = f'<h3 id="title" style="left:96px;top:40px;width:1700px;height:60px">{label}</h3>'
    return f"<section>{title}{''.join(boxes)}</section>"


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "wrap-check.pptx")
    sections = [
        (f"{i:02d}.html", _section(i, size, width))
        for i, (size, width) in enumerate(((s, w) for s in _SIZES for w in _WIDTHS), start=1)
    ]
    report = compile_sections(sections, out)
    for error in report.errors():
        print(error)
    print(f"wrote {out}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
