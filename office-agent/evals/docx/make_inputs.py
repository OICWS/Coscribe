"""Builds the input files of the Word tasks (the notes, a PDF to summarise, the contract and the
handbook to edit, the user's letterhead, an image), so they are reproducible rather than opaque.
The outputs are committed.

    python -m evals.docx.make_inputs
"""

# ruff: noqa: E501 -- the inputs are text a person reads, not code
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Pt, RGBColor
from PIL import Image, ImageDraw

TASKS = Path(__file__).resolve().parent / "tasks"

NOTES_MD = """\
# Warehouse move: notes from the March review

Attendees: Dana (ops), Luis (finance), Mei (IT). Rough notes, not minutes.

- The lease on the old warehouse in Leeds ends on 30 June 2026; the new site in Wakefield is 14 miles away.
- Moving cost was quoted at 184,000 GBP by Northline; the budget set aside is 200,000 GBP.
- Racking: 40 pallet racks move, 12 are scrapped (rust). Replacement racks are 310 GBP each.
- Mei: the barcode scanners (35 units) need a new wifi survey, 6,500 GBP, two weeks of lead time.
- Dana wants the move over a weekend: Friday 19 June to Sunday 21 June, so stock is picked again on Monday 22 June.
- Risk: the Wakefield site's loading doors are 3.2 m high, two of our trailers are 3.4 m. Need to hire lower trailers, about 1,800 GBP.
- Luis: insurance for goods in transit adds 4,200 GBP.
- Open question: do we keep the Leeds mezzanine? Nobody decided.
- Next steps: Dana signs the Northline quote by 10 April; Mei books the survey; Luis updates the budget.
"""

QUOTE_LINES = [
    ("Northline Logistics Ltd", True),
    ("Quotation Q-2026-0412", True),
    ("Date: 2 March 2026   Valid until: 2 April 2026", False),
    ("Customer: Harbour Foods Ltd", False),
    ("", False),
    ("Scope: relocation of dry goods warehouse, Leeds to Wakefield, 14 miles.", False),
    ("Labour: 12 operatives x 2 days x 4 hours rate 38 GBP/h ......... 3,648 GBP", False),
    ("Vehicles: 6 curtain-side trailers x 2 days ........................ 14,400 GBP", False),
    ("Racking dismantle and refit: 40 racks x 95 GBP ................... 3,800 GBP", False),
    ("Project management ............................................. 6,500 GBP", False),
    ("Contingency (10%) ............................................... 2,835 GBP", False),
    ("Total (excluding VAT) ........................................... 31,183 GBP", False),
    ("", False),
    ("Terms: 30% deposit on acceptance, balance 14 days after completion.", False),
    ("Exclusions: insurance of goods in transit, replacement racking, IT equipment.", False),
    ("Earliest start: 15 June 2026. A weekend move needs 3 weeks' notice.", False),
]

CLAUSES = [
    (
        "1. Services",
        "The Supplier shall provide the managed print services described in Schedule A.",
    ),
    (
        "2. Term",
        "This Agreement starts on 1 April 2026 and continues for 12 months unless ended earlier under clause 8.",
    ),
    ("3. Fees", "The Customer shall pay the monthly fee of 2,400 GBP set out in Schedule B."),
    (
        "4. Payment",
        "The Customer shall pay each invoice within 30 days of the date of the invoice.",
    ),
    (
        "5. Liability",
        "The Supplier's total liability under this Agreement is limited to the fees paid in the preceding 12 months.",
    ),
    (
        "6. Confidentiality",
        "Each party shall keep the other party's confidential information secret and use it only for this Agreement.",
    ),
    (
        "7. Data protection",
        "Each party shall comply with the data protection laws that apply to it.",
    ),
    ("8. Termination", "Either party may end this Agreement by giving 60 days' written notice."),
]

HANDBOOK = [
    (
        "Onboarding",
        [
            "New starters get a laptop and an account on their first day.",
            "A buddy is assigned for the first four weeks.",
        ],
    ),
    (
        "Working hours",
        [
            "Core hours are 10:00 to 16:00; the rest is flexible.",
            "Overtime is agreed with the team lead in advance.",
        ],
    ),
    (
        "Safety",
        [
            "Report any accident to the duty manager within one hour.",
            "Fire exits are checked every Monday morning.",
        ],
    ),
    (
        "Expenses",
        [
            "Claims are made in the expenses tool within 30 days.",
            "Receipts are required for every amount over 25 GBP.",
        ],
    ),
]

SALES_CSV = """\
Region,Quarter,Product,Units,Revenue
North,Q1,Alpha,120,14400
North,Q2,Alpha,150,18000
North,Q3,Beta,90,13500
North,Q4,Beta,110,16500
South,Q1,Alpha,200,24000
South,Q2,Gamma,80,16000
South,Q3,Gamma,95,19000
South,Q4,Alpha,210,25200
East,Q1,Beta,60,9000
East,Q2,Beta,70,10500
East,Q3,Alpha,130,15600
East,Q4,Gamma,100,20000
West,Q1,Gamma,40,8000
West,Q2,Alpha,90,10800
West,Q3,Beta,85,12750
West,Q4,Beta,95,14250
"""

BILINGUAL_MD = """\
# 新员工入职说明 / New starter guide

- 入职日期：2026 年 5 月 6 日（周三），上午 9:30 到前台报到。Start date: Wednesday 6 May 2026, arrive at reception by 09:30.
- 部门：数据平台组 (Data Platform)，直属经理：陈静 Jing Chen。
- 笔记本电脑和门禁卡在第一天发放；IT 热线 8800。Laptop and badge are issued on day one; IT hotline 8800.
- 试用期 3 个月，转正评估在 2026 年 8 月 6 日。Probation lasts 3 months; the review is on 6 August 2026.
- 午餐补贴每天 35 元 / lunch allowance 35 CNY per working day.
- 第一周培训：安全 (Mon)、数据规范 (Tue)、内部工具 (Wed–Thu)、答疑 (Fri)。
"""


def _letterhead(path: Path) -> None:
    document = Document()
    body = document.styles.add_style("Letter Body", WD_STYLE_TYPE.PARAGRAPH)
    body.base_style = document.styles["Normal"]
    body.font.name = "Georgia"
    body.font.size = Pt(11)
    body.paragraph_format.space_after = Pt(8)
    sender = document.styles.add_style("Letter Sender", WD_STYLE_TYPE.PARAGRAPH)
    sender.base_style = document.styles["Normal"]
    sender.font.name = "Georgia"
    sender.font.size = Pt(9)
    sender.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    header = document.sections[0].header.paragraphs[0]
    header.text = "ACME Corporation, 12 Mill Lane, Leeds LS1 4AB"
    header.style = sender
    document.sections[0].footer.paragraphs[0].text = "Registered in England, no. 04417281"
    # The file is a letterhead: styles, header and footer, and no body text.
    document.save(path)


def _contract(path: Path) -> None:
    document = Document()
    document.add_heading("Managed Print Services Agreement", level=0)
    document.add_paragraph(
        "Between Pennine Print Ltd (the Supplier) and Harbour Foods Ltd (the Customer)."
    )
    for title, text in CLAUSES:
        document.add_heading(title, level=2)
        document.add_paragraph(text)
    document.save(path)


def _handbook(path: Path) -> None:
    document = Document()
    document.add_heading("Staff handbook", level=0)
    document.add_paragraph("This handbook sets out how we work. It applies to all staff.")
    for title, items in HANDBOOK:
        document.add_heading(title, level=1)
        for item in items:
            document.add_paragraph(item, style="List Bullet")
    document.add_heading("Contacts", level=1)
    table = document.add_table(rows=3, cols=2)
    table.style = "Table Grid"
    for row, (name, who) in enumerate(
        [("Duty manager", "ext. 201"), ("HR", "ext. 305"), ("IT desk", "ext. 410")]
    ):
        table.cell(row, 0).text = name
        table.cell(row, 1).text = who
    document.save(path)


WEEKLY_SECTIONS = [
    ("一、本周概况", ["本周华东区 4 个项目按计划推进，整体进度 72%。", "客户满意度调查回收 38 份，平均 4.6 分。"]),
    ("二、项目进展", ["各项目进度如下表。"]),
    ("三、问题与风险", ["苏州仓库的网络改造延期一周，影响系统切换。", "宁波项目缺少一名测试工程师。"]),
    ("四、旧流程说明（已废止）", ["原纸质审批单自 5 月 1 日起停止使用，相关说明不再适用。"]),
    ("五、联系人", ["项目负责人：陈静，分机 3021。"]),
]


def _weekly_report(path: Path, chart: Path) -> None:
    document = Document()
    document.sections[0].header.paragraphs[0].text = "华东区项目周报"
    document.sections[0].footer.paragraphs[0].text = "内部资料，请勿外传"
    document.add_heading("华东区项目周报（第 24 周）", level=0)
    for title, lines in WEEKLY_SECTIONS:
        document.add_heading(title, level=1)
        for line in lines:
            document.add_paragraph(line)
        if title.startswith("二"):
            table = document.add_table(rows=4, cols=2)
            table.style = "Light Grid Accent 1"
            for row, cells in enumerate(
                [("项目", "进度"), ("苏州仓储", "65%"), ("宁波门店", "80%"), ("上海总部", "71%")]
            ):
                for col, text in enumerate(cells):
                    table.cell(row, col).text = text
            document.add_picture(str(chart))
    document.save(path)


def _progress_chart(path: Path) -> None:
    image = Image.new("RGB", (480, 240), "white")
    draw = ImageDraw.Draw(image)
    for index, value in enumerate((65, 80, 71)):
        left = 60 + index * 140
        draw.rectangle([left, 220 - value * 2, left + 80, 220], fill=(31, 78, 121))
    draw.line([40, 220, 460, 220], fill="black", width=2)
    image.save(path)


def _quote_pdf(path: Path) -> None:
    from reportlab.pdfgen import canvas

    page = canvas.Canvas(str(path))
    y = 800
    for text, bold in QUOTE_LINES:
        page.setFont("Helvetica-Bold" if bold else "Helvetica", 13 if bold else 10)
        page.drawString(60, y, text)
        y -= 22
    page.save()


def _diagram(path: Path) -> None:
    image = Image.new("RGB", (1200, 700), "#f5f7fa")
    draw = ImageDraw.Draw(image)
    boxes = [
        (80, 260, 380, 440, "#2f6fdb"),
        (450, 260, 750, 440, "#e08a1e"),
        (820, 260, 1120, 440, "#2a9d6f"),
    ]
    for left, top, right, bottom, color in boxes:
        draw.rounded_rectangle([left, top, right, bottom], radius=24, fill=color)
    for start, end in ((380, 450), (750, 820)):
        draw.line([start + 10, 350, end - 10, 350], fill="#333333", width=8)
        draw.polygon([(end - 10, 350), (end - 40, 330), (end - 40, 370)], fill="#333333")
    image.save(path)


CLIENT_BRIEF_MD = """\
# Northwind Logistics: what they asked for (call notes, 3 Sept 2026)

- Contact: Priya Raman, Head of Operations, Northwind Logistics (Leeds).
- Problem: drivers re-key delivery notes into three systems; about 40 minutes per driver per day.
  Errors in 6% of invoices last quarter.
- They want: one mobile form that feeds the warehouse system, invoicing and the customer portal.
- Must work offline in the vans; 140 drivers; Android only.
- Go-live wanted before 1 March 2027 (peak season ends then).
- Budget signal: "under 150k for the first year".
- Decision by their board on 21 October 2026. They want the proposal by 10 October.
- Our team: Daniel Cho (delivery lead), Ana Ruiz (Android), Tom Price (integration).
- Our approach, agreed internally: 2-week discovery, then three 4-week build sprints, pilot with
  20 drivers in January, full rollout in February.
- Risk they raised: the customer portal vendor's API is undocumented.
"""

PRICING_CSV = """\
Item,Amount (GBP)
Discovery (2 weeks),12000
Build sprints (3 x 4 weeks),84000
Pilot support (20 drivers),9500
Rollout and training (140 drivers),14000
Year-one support,18000
"""

HALF_YEAR_CSV = """\
月份,营收(万元),新客户数,客户满意度
1月,812,34,91.2
2月,705,28,90.5
3月,968,41,92.8
4月,1023,45,93.1
5月,1110,52,92.4
6月,1187,57,94.0
"""

HALF_YEAR_NOTES_MD = """\
# 华东销售部 2026 年上半年要点（部门内部记录）

- 上半年营收 5805 万元，完成全年目标 11000 万元的 52.8%。
- 新客户 257 家；6 月新客户数为上半年最高。
- 客户满意度从 1 月的 91.2 提升到 6 月的 94.0。
- 2 月受春节影响营收最低（705 万元）。
- 上线了新的报价系统，报价周期从 3 天缩短到 1 天。
- 问题：苏州大客户流失 1 家，原因是交付延期；人员流动率 12%。
- 下半年计划：重点开拓南京市场；6 名新人在 8 月前完成培训；把交付准时率提升到 98%。
"""


def main() -> None:
    def put(task: str, name: str) -> Path:
        folder = TASKS / task / "inputs"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / name

    put("01-report-from-notes", "warehouse_notes.md").write_text(NOTES_MD, encoding="utf-8")
    _quote_pdf(put("02-memo-from-pdf", "northline_quote.pdf"))
    _contract(put("03-tracked-contract", "service_agreement.docx"))
    _letterhead(put("04-letter-on-template", "letterhead.docx"))
    put("05-table-heavy", "sales.csv").write_text(SALES_CSV, encoding="utf-8")
    put("06-mixed-language", "入职说明.md").write_text(BILINGUAL_MD, encoding="utf-8")
    _handbook(put("07-restructure", "handbook.docx"))
    _diagram(put("08-image-caption", "process.png"))
    put("09-proposal", "northwind_brief.md").write_text(CLIENT_BRIEF_MD, encoding="utf-8")
    put("09-proposal", "pricing.csv").write_text(PRICING_CSV, encoding="utf-8")
    put("10-half-year-summary", "上半年数据.csv").write_text(HALF_YEAR_CSV, encoding="utf-8")
    put("10-half-year-summary", "上半年要点.md").write_text(HALF_YEAR_NOTES_MD, encoding="utf-8")
    chart = put("11-restructure-report", "progress.png")
    _progress_chart(chart)
    _weekly_report(put("11-restructure-report", "weekly_report.docx"), chart)
    chart.unlink()


if __name__ == "__main__":
    main()
