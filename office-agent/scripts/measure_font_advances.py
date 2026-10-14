"""Measure glyph advances of the Windows fonts decks use, in the emitter's table format.

The copied emitter (`tools/_native_svg/.../drawingml/font_advances.json`) sizes a text box from
per-character advances measured on fonts bundled with PowerPoint for Mac. It has none for the
CJK families pages are written in (Microsoft YaHei first), so their Latin letters and digits are
guessed at 0.55 em. This script measures them where those fonts are: on Windows, in
C:/Windows/Fonts (the Windows CI job). Same method as upstream: FreeType at 1000 px, no kerning,
the advance of each character alone, rounded to 4 decimals, for the characters upstream lists.

    python scripts/measure_font_advances.py C:/Windows/Fonts --out table.json
    python scripts/measure_font_advances.py C:/Windows/Fonts --check <the committed table>

`--check` measures again and fails when a committed advance differs, or a font the table has
is missing, so the table cannot drift from the fonts it claims to describe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import ImageFont

_DRAWINGML = (
    Path(__file__).resolve().parents[1] / "src/coscribe/tools/_native_svg/svg_to_pptx/drawingml"
)
SIZE = 1000
TOLERANCE = 0.001

# family -> style -> (file, index in a .ttc)
FONTS: dict[str, dict[str, tuple[str, int]]] = {
    "microsoft yahei": {"regular": ("msyh.ttc", 0), "bold": ("msyhbd.ttc", 0)},
    "microsoft yahei ui": {"regular": ("msyh.ttc", 1), "bold": ("msyhbd.ttc", 1)},
    "microsoft yahei light": {"regular": ("msyhl.ttc", 0)},
    "dengxian": {"regular": ("Deng.ttf", 0), "bold": ("Dengb.ttf", 0)},
    "simhei": {"regular": ("simhei.ttf", 0)},
    "simsun": {"regular": ("simsun.ttc", 0)},
    "kaiti": {"regular": ("simkai.ttf", 0)},
    "fangsong": {"regular": ("simfang.ttf", 0)},
    "microsoft jhenghei": {"regular": ("msjh.ttc", 0), "bold": ("msjhbd.ttc", 0)},
    "segoe ui": {"regular": ("segoeui.ttf", 0), "bold": ("segoeuib.ttf", 0)},
}
# Upstream measured these on the Mac; measured here only to report whether Windows agrees.
COMPARED: dict[str, dict[str, tuple[str, int]]] = {
    "arial": {"regular": ("arial.ttf", 0), "bold": ("arialbd.ttf", 0)},
    "calibri": {"regular": ("calibri.ttf", 0), "bold": ("calibrib.ttf", 0)},
    "times new roman": {"regular": ("times.ttf", 0)},
}


def _characters() -> list[str]:
    table = json.loads((_DRAWINGML / "font_advances.json").read_text(encoding="utf-8"))
    return list(table["families"]["arial"]["regular"]["advances"])


def _measure(path: Path, index: int, characters: list[str]) -> tuple[str, dict[str, float]]:
    font = ImageFont.truetype(str(path), SIZE, index=index, layout_engine=ImageFont.Layout.BASIC)
    name = " ".join(part for part in font.getname() if part)
    # A soft hyphen is not drawn unless the line breaks there; upstream counts it as 0.
    return name, {
        ch: 0.0 if ch == "\xad" else round(font.getlength(ch) / SIZE, 4) for ch in characters
    }


Table = dict[str, dict[str, dict[str, Any]]]


def measure(
    fonts_dir: Path, wanted: dict[str, dict[str, tuple[str, int]]]
) -> tuple[Table, list[str]]:
    characters = _characters()
    families: Table = {}
    missing = []
    for family, styles in wanted.items():
        for style, (file, index) in styles.items():
            path = fonts_dir / file
            if not path.exists():
                missing.append(f"{family} {style} ({file})")
                continue
            face, advances = _measure(path, index, characters)
            families.setdefault(family, {})[style] = {"face": face, "advances": advances}
    return families, missing


def _differences(old: Table, new: Table) -> list[str]:
    found = []
    for family, styles in old.items():
        for style, entry in styles.items():
            fresh = new.get(family, {}).get(style)
            if fresh is None:
                found.append(f"{family} {style}: font not found")
                continue
            for ch, advance in entry["advances"].items():
                now = fresh["advances"].get(ch, -1)
                if abs(now - advance) > TOLERANCE:
                    found.append(f"{family} {style} {ch!r}: {advance} -> {now}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("fonts_dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()

    families, missing = measure(args.fonts_dir, FONTS)
    for line in missing:
        print(f"missing: {line}")
    upstream = json.loads((_DRAWINGML / "font_advances.json").read_text(encoding="utf-8"))
    compared, _ = measure(args.fonts_dir, COMPARED)
    for line in _differences(
        {f: {s: upstream["families"][f][s] for s in compared[f]} for f in compared}, compared
    )[:20]:
        print(f"differs from upstream's Mac measurement: {line}")

    if args.check:
        committed = json.loads(args.check.read_text(encoding="utf-8"))["families"]
        found = _differences(committed, families)
        for line in found:
            print(f"changed: {line}")
        return 1 if found else 0

    table = {
        "schema": "ppt-master.font-advances.v1",
        "unit": "em (advance ÷ font size), measured with FreeType at 1000 px, no kerning",
        "source": "Windows fonts (C:/Windows/Fonts), by scripts/measure_font_advances.py",
        "families": families,
    }
    text = json.dumps(table, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    print(f"measured: {', '.join(f'{f} ({len(s)})' for f, s in families.items())}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
