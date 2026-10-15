"""Builds the binary input files of the tasks (images, the user's own template, the deck to
edit), so they are reproducible rather than opaque. The outputs are committed.

    python -m evals.pptx.make_inputs
"""

from __future__ import annotations

import shutil
import tempfile
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


_SVG = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" font-family="Microsoft YaHei, Arial"'
_BENEFITS = [
    ("护眼无频闪", "光线稳定不频闪，长时间读写更舒服"),
    ("旋钮一键调光", "一颗旋钮，亮度与色温随时调好"),
    ("可折叠随身带", "机身 480 克，折叠收起放进包里"),
]


def _built_deck(path: Path) -> None:
    """A deck built from pages, as a colleague hands it on: the .pptx only, no pages to rebuild
    from, so a change goes through the edit tools; the benefits are groups."""
    from coscribe.tools.office.pptx.engine import compile_pages

    cover = (
        f'<svg {_SVG}><rect width="1280" height="720" fill="#0F172A"/>'
        '<text id="title" x="96" y="320" font-size="56" font-weight="bold" fill="#FFFFFF">'
        "云朵 Pro 智能台灯</text>"
        '<text id="price" x="96" y="400" font-size="28" fill="#FBBF24">首发价 399 元</text></svg>'
    )
    items = "".join(
        f'<g id="benefit-{i}"><circle cx="128" cy="{216 + 140 * (i - 1)}" r="22" fill="#C2410C"/>'
        f'<text x="128" y="{224 + 140 * (i - 1)}" font-size="20" font-weight="bold" fill="#FFFFFF"'
        f' text-anchor="middle">0{i}</text>'
        f'<text x="176" y="{214 + 140 * (i - 1)}" font-size="30" font-weight="bold" fill="#0E1116">'
        f"{name}</text>"
        f'<text x="176" y="{252 + 140 * (i - 1)}" font-size="20" fill="#4B5563">{detail}</text></g>'
        for i, (name, detail) in enumerate(_BENEFITS, start=1)
    )
    benefits = (
        f'<svg {_SVG}><rect width="1280" height="720" fill="#F5F3EF"/>'
        '<text id="title" x="96" y="120" font-size="40" font-weight="bold" fill="#0E1116">'
        f"三个理由，把它放在手边</text>{items}</svg>"
    )
    launch = (
        f'<svg {_SVG}><rect width="1280" height="720" fill="#F5F3EF"/>'
        '<text id="title" x="96" y="120" font-size="40" font-weight="bold" fill="#0E1116">'
        "11 月 18 日首发</text>"
        '<g id="offer"><rect x="96" y="220" width="640" height="200" rx="16" fill="#FFFFFF"/>'
        '<text x="128" y="300" font-size="36" font-weight="bold" fill="#C2410C">399 元</text>'
        '<text x="128" y="360" font-size="22" fill="#4B5563">前 1,000 名下单再减 50 元</text>'
        "</g></svg>"
    )
    pages = [("01-cover", cover), ("02-benefits", benefits), ("03-launch", launch)]
    report = compile_pages(pages, path)
    assert not report.errors(), report.errors()


def _photo(path: Path, sky: str, kind: str) -> None:
    image = Image.new("RGB", (1200, 800), sky)
    draw = ImageDraw.Draw(image)
    if kind == "store":
        draw.rectangle([0, 560, 1200, 800], fill="#9a9a9a")
        draw.rectangle([220, 180, 980, 600], fill="#f2efe8")
        draw.rectangle([220, 180, 980, 260], fill="#1f4e79")
        draw.rectangle([300, 320, 560, 600], fill="#6fa3c7")
        draw.rectangle([640, 320, 900, 520], fill="#6fa3c7")
    elif kind == "team":
        draw.rectangle([0, 600, 1200, 800], fill="#c8b89a")
        for i, colour in enumerate(["#2f4858", "#86bbd8", "#f6ae2d", "#f26419", "#33658a"]):
            x = 200 + i * 200
            draw.ellipse([x - 55, 250, x + 55, 360], fill="#e9c9a8")
            draw.rectangle([x - 80, 370, x + 80, 640], fill=colour)
    else:
        draw.ellipse([350, 150, 850, 650], fill="#1f4e79")
        draw.rectangle([520, 300, 680, 500], fill="#ffffff")
    image.save(path)


def _rough_deck(path: Path) -> None:
    """A first draft as a user makes one: the default theme, bullets, a wall of text, photos
    dropped in, a native chart and a table. The content is right; the design is not."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.dml.color import RGBColor
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches, Pt

    # The photos are only inside the deck, as a user hands it over.
    folder = Path(tempfile.mkdtemp())
    for name, sky, kind in [
        ("store.png", "#bcd4e6", "store"),
        ("team.png", "#e8e2d6", "team"),
        ("logo.png", "#ffffff", "logo"),
    ]:
        _photo(folder / name, sky, kind)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    def bullets(title: str, lines: list[str]) -> object:
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = title
        body = s.placeholders[1].text_frame
        body.text = lines[0]
        for line in lines[1:]:
            body.add_paragraph().text = line
        return s

    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = "2025 年华东区销售总结"
    cover.placeholders[1].text = "华东大区 销售部 王磊 2026年1月"
    bullets(
        "全年概况",
        [
            "2025 年华东区全年销售额 5,560 万元，比 2024 年的 4,630 万元增长 20.1%，完成年度目标的 103%",
            "新开门店 12 家，门店总数达到 86 家，其中上海 31 家、杭州 22 家、南京 18 家、苏州 15 家",
            "会员人数突破 42 万，会员复购率 38%，比上年提高 5 个百分点",
            "线上渠道销售额 1,240 万元，占比 22%，第四季度上线了小程序商城",
            "客单价 286 元，同比提升 6%",
            "主要问题：南京两家老店租约到期关闭，苏州新店爬坡慢于预期",
        ],
    )
    stores = prs.slides.add_slide(prs.slide_layouts[5])
    stores.shapes.title.text = "门店与团队"
    stores.shapes.add_picture(str(folder / "store.png"), Inches(0.6), Inches(1.6), Inches(5.2))
    stores.shapes.add_picture(str(folder / "team.png"), Inches(6.9), Inches(2.3), Inches(4.6))
    caption = stores.shapes.add_textbox(Inches(0.6), Inches(5.3), Inches(5), Inches(0.6))
    caption.text_frame.text = "上海淮海路旗舰店（2025 年 6 月开业）"
    team = stores.shapes.add_textbox(Inches(6.9), Inches(5.6), Inches(5), Inches(0.6))
    team.text_frame.text = "华东区销售团队 共 214 人"
    team.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0x00, 0x00)
    quarters = prs.slides.add_slide(prs.slide_layouts[5])
    quarters.shapes.title.text = "分季度销售额（万元）"
    data = CategoryChartData()
    data.categories = ["Q1", "Q2", "Q3", "Q4"]
    data.add_series("销售额", (1180, 1320, 1410, 1650))
    quarters.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1.6), Inches(8), Inches(5), data
    )
    cities = prs.slides.add_slide(prs.slide_layouts[5])
    cities.shapes.title.text = "各城市业绩"
    rows = [
        ["城市", "销售额（万元）", "同比"],
        ["上海", "2,310", "+18%"],
        ["杭州", "1,420", "+26%"],
        ["南京", "980", "+9%"],
        ["苏州", "850", "+31%"],
    ]
    table = cities.shapes.add_table(5, 3, Inches(1), Inches(1.7), Inches(9), Inches(3.5)).table
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    plan = bullets(
        "2026 年计划",
        ["销售额目标 6,500 万元", "新开门店 15 家，重点在杭州和苏州", "会员人数目标 55 万"],
    )
    plan.shapes.add_picture(str(folder / "logo.png"), Inches(11.4), Inches(0.3), Inches(1.4))
    for paragraph in plan.placeholders[1].text_frame.paragraphs:
        paragraph.runs[0].font.size = Pt(32)
    prs.save(path)


def main() -> None:
    images = TASKS / "04-product-launch" / "inputs"
    images.mkdir(parents=True, exist_ok=True)
    _lamp_image(images / "lamp-front.png", "#e9edf2", desk=False, close=False)
    _lamp_image(images / "lamp-scene.png", "#c9d6e2", desk=True, close=False)
    _lamp_image(images / "lamp-detail.png", "#2b2b30", desk=False, close=True)
    shutil.copyfile(TEMPLATE, TASKS / "06-own-template" / "inputs" / "公司模板.pptx")
    _edit_deck(TASKS / "07-edit-deck" / "inputs" / "季度汇报.pptx")
    built = TASKS / "11-edit-built-deck" / "inputs"
    built.mkdir(parents=True, exist_ok=True)
    _built_deck(built / "新品发布.pptx")
    rough = TASKS / "15-beautify-deck" / "inputs"
    rough.mkdir(parents=True, exist_ok=True)
    _rough_deck(rough / "华东销售总结.pptx")


if __name__ == "__main__":
    main()
