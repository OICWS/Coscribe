"""The Slides panel's downloads besides the .pptx itself: a PDF, a web page and a .pptx in basic
fonts. Each is made from the built deck, so it shows what the .pptx holds.
"""

from __future__ import annotations

import base64
import io
import json
import re
import tempfile
import zipfile
from html import escape
from pathlib import Path

from ...._office_com import convert
from .view import read_deck, slide_svg

# PowerPoint's own export is the best PDF there is; past this the job is taken for hung.
_OFFICE_TIMEOUT = 90.0
# Twice the 1280-wide page: sharp when the PDF is zoomed to fill a screen.
_RASTER_WIDTH = 2560
# A 16:9 page in points (13.33 × 7.5 in), PowerPoint's own widescreen size.
_PDF_PAGE = (960.0, 540.0)

# Fonts every Windows with Office has. Any other face is swapped for one of these, by its kind.
_BASIC = {
    name.lower()
    for name in (
        "Arial", "Calibri", "Calibri Light", "Cambria", "Consolas", "Courier New", "Georgia",
        "Segoe UI", "Tahoma", "Times New Roman", "Verdana", "Microsoft YaHei", "微软雅黑",
        "SimSun", "宋体", "SimHei", "黑体", "KaiTi", "楷体", "DengXian", "等线",
    )
}  # fmt: skip
_SERIF = re.compile(r"serif|song|ming|times|georgia|garamond|cambria|宋|明", re.I)
_SANS_SERIF = re.compile(r"sans", re.I)
_FACE = re.compile(r'(<a:(latin|ea|cs)\b[^>]*?\btypeface=")([^"]*)(")')
_FONT_PARTS = re.compile(r"ppt/(slides|slideLayouts|slideMasters|theme|notesSlides)/[^/]+\.xml$")


def deck_pdf(deck: Path, workspace: Path) -> bytes:
    """The deck as a PDF: PowerPoint's own export where it is installed, else each slide drawn at
    twice the page size, a page each."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / f"{deck.stem}.pdf"
        try:
            if convert(deck, target, "pdf", _OFFICE_TIMEOUT) is not None and target.is_file():
                return target.read_bytes()
        except ValueError:
            pass  # the program failed or hung: the drawn copy below still shows every slide
    return _drawn_pdf(deck, workspace)


def deck_html(deck: Path, workspace: Path) -> str:
    """One web page with every slide and a small player: arrow keys or a click move between
    slides. The slides are images, so the page runs only its own few lines."""
    view = read_deck(deck)
    images = [
        "data:image/svg+xml;base64,"
        + base64.b64encode(slide_svg(deck, i, workspace).encode("utf-8")).decode()
        for i, slide in enumerate(view["slides"])
        if slide["kind"] == "page"
    ]
    return _PLAYER.replace("__TITLE__", escape(view["title"])).replace(
        "__SLIDES__", json.dumps(images)
    )


def deck_basic_fonts(deck: Path) -> bytes:
    """The .pptx with every face a computer may lack swapped for a basic one: Microsoft YaHei
    for Chinese and sans-serif text, Times New Roman or SimSun for serif."""
    out = io.BytesIO()
    with zipfile.ZipFile(deck) as source, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as copy:
        for item in source.infolist():
            data = source.read(item.filename)
            if _FONT_PARTS.match(item.filename):
                data = _FACE.sub(_basic_face, data.decode("utf-8")).encode("utf-8")
            copy.writestr(item, data)
    return out.getvalue()


def _basic_face(match: re.Match[str]) -> str:
    start, kind, face, end = match.group(1), match.group(2), match.group(3), match.group(4)
    if not face or face.startswith("+") or face.lower() in _BASIC:
        return match.group(0)
    serif = bool(_SERIF.search(face)) and not _SANS_SERIF.search(face)
    if kind == "ea":
        basic = "SimSun" if serif else "Microsoft YaHei"
    else:
        basic = "Times New Roman" if serif else "Arial"
    return f"{start}{basic}{end}"


def _drawn_pdf(deck: Path, workspace: Path) -> bytes:
    import resvg_py
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    out = io.BytesIO()
    pdf = canvas.Canvas(out, pagesize=_PDF_PAGE)
    pdf.setTitle(deck.stem)
    for i, slide in enumerate(read_deck(deck)["slides"]):
        if slide["kind"] == "page":
            png = resvg_py.svg_to_bytes(
                svg_string=slide_svg(deck, i, workspace), width=_RASTER_WIDTH
            )
            pdf.drawImage(ImageReader(io.BytesIO(bytes(png))), 0, 0, *_PDF_PAGE)
        pdf.showPage()
    pdf.save()
    return out.getvalue()


_PLAYER = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>__TITLE__</title>
<style>
html,body{margin:0;height:100%;background:#000;overflow:hidden;font:14px system-ui,sans-serif}
img{position:absolute;inset:0;margin:auto;max-width:100%;max-height:calc(100% - 44px);top:-44px}
nav{position:fixed;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:6px;
align-items:center;color:#fff;background:#262524;border-radius:999px;padding:4px 10px}
button{background:none;border:0;color:#fff;font-size:18px;cursor:pointer;padding:2px 8px}
</style></head><body>
<img id="slide" alt="">
<nav><button id="prev" aria-label="Previous slide">&#8249;</button><span id="page"></span>
<button id="next" aria-label="Next slide">&#8250;</button></nav>
<script>
const slides = __SLIDES__;
let at = 0;
const show = (i) => {
  at = Math.max(0, Math.min(slides.length - 1, i));
  document.getElementById("slide").src = slides[at];
  document.getElementById("page").textContent = (at + 1) + " / " + slides.length;
};
document.getElementById("prev").onclick = () => show(at - 1);
document.getElementById("next").onclick = () => show(at + 1);
document.getElementById("slide").onclick = () => show(at + 1);
addEventListener("keydown", (e) => {
  if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(e.key)) show(at + 1);
  if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) show(at - 1);
  if (e.key === "Home") show(0);
  if (e.key === "End") show(slides.length - 1);
});
show(0);
</script></body></html>
"""
