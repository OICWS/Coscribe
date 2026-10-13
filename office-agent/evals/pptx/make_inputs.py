"""Builds the binary input files of the tasks (images, the user's own template, the deck to
edit), so they are reproducible rather than opaque. The outputs are committed.

    python -m evals.pptx.make_inputs
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw

TASKS = Path(__file__).resolve().parent / "tasks"
TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "src/coscribe/builtin_templates/pptx/modern-block/template.pptx"
)


def _lamp_image(path: Path, background: str, desk: bool, close: bool) -> None:
    image = Image.new("RGB", (1200, 800), background)
    draw = ImageDraw.Draw(image)
    if desk:
        draw.rectangle([0, 600, 1200, 800], fill="#8b6b4a")
        draw.rectangle([780, 540, 1000, 600], fill="#f4f1ea")
    scale = 1.6 if close else 1.0
    cx, base = 600, 600 if not close else 740
    draw.ellipse(
        [cx - 90 * scale, base - 20 * scale, cx + 90 * scale, base + 20 * scale], fill="#d9d4c7"
    )
    draw.line(
        [cx, base, cx - 70 * scale, base - 210 * scale], fill="#e8e4da", width=int(14 * scale)
    )
    draw.line(
        [cx - 70 * scale, base - 210 * scale, cx + 120 * scale, base - 300 * scale],
        fill="#e8e4da",
        width=int(14 * scale),
    )
    draw.ellipse(
        [cx + 90 * scale, base - 340 * scale, cx + 210 * scale, base - 260 * scale], fill="#fff6d6"
    )
    draw.ellipse([cx - 24, base - 8, cx + 24, base + 8], fill="#f0a93c")
    image.save(path)


def _edit_deck(path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    def slide(title: str, lines: list[str]) -> None:
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        body = s.placeholders[1].text_frame
        body.text = lines[0]
        for line in lines[1:]:
            body.add_paragraph().text = line

    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = "2026 年第三季度经营汇报"
    cover.placeholders[1].text = "财务部 · 2026 年 10 月"
    revenue = prs.slides.add_slide(prs.slide_layouts[5])
    revenue.shapes.title.text = "Q3 营收"
    table = revenue.shapes.add_table(3, 3, Inches(0.9), Inches(1.8), Inches(8), Inches(2.4)).table
    for r, row in enumerate(
        [["指标", "Q3", "同比"], ["营收", "1,280 万元", "+8%"], ["毛利率", "41%", "+2 个点"]]
    ):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    box = revenue.shapes.add_textbox(Inches(0.9), Inches(4.6), Inches(11), Inches(1.2))
    box.text_frame.text = "Q3 营收 1,280 万元，同比增长 +8%，主要来自企业软件。"
    box.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    slide("增长来源", ["企业软件订阅续约率 94%", "西南新市场贡献 210 万元", "智能硬件持平"])
    slide("Q4 重点", ["追回华北延迟订单", "东南亚扩充渠道", "企业软件发布新版本"])
    prs.save(path)


def main() -> None:
    images = TASKS / "04-product-launch" / "inputs"
    images.mkdir(parents=True, exist_ok=True)
    _lamp_image(images / "lamp-front.png", "#e9edf2", desk=False, close=False)
    _lamp_image(images / "lamp-scene.png", "#c9d6e2", desk=True, close=False)
    _lamp_image(images / "lamp-detail.png", "#2b2b30", desk=False, close=True)
    shutil.copyfile(TEMPLATE, TASKS / "06-own-template" / "inputs" / "公司模板.pptx")
    _edit_deck(TASKS / "07-edit-deck" / "inputs" / "季度汇报.pptx")


if __name__ == "__main__":
    main()
