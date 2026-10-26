"""Reference solutions of the Word evaluation tasks: what a good answer looks like, built with
python-docx. They show that every task can be solved and that its `expect.json` accepts it."""

from __future__ import annotations

import copy
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches

_STAMP = {qn("w:id"): "0", qn("w:author"): "Claude", qn("w:date"): "2026-06-15T09:00:00Z"}


def _stamped(tag: str, ident: int) -> OxmlElement:
    element = OxmlElement(tag)
    for key, value in _STAMP.items():
        element.set(key, value)
    element.set(qn("w:id"), str(ident))
    return element


def _run(text: str, deleted: bool = False) -> OxmlElement:
    run = OxmlElement("w:r")
    node = OxmlElement("w:delText" if deleted else "w:t")
    node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = text
    run.append(node)
    return run


def redline(paragraph, old: str, new: str, ident: int) -> None:
    """Replace `old` by `new` inside a one-run paragraph as a tracked deletion plus insertion."""
    run = paragraph.runs[0]
    before, _, after = run.text.partition(old)
    holder = run._r
    for text in (before,):
        if text:
            holder.addprevious(_run(text))
    deletion = _stamped("w:del", ident)
    deletion.append(_run(old, deleted=True))
    insertion = _stamped("w:ins", ident + 1)
    insertion.append(_run(new))
    holder.addprevious(deletion)
    holder.addprevious(insertion)
    if after:
        holder.addprevious(_run(after))
    holder.getparent().remove(holder)


def _inserted_paragraph(document, anchor, style: str, text: str, ident: int):
    paragraph = copy.deepcopy(anchor._p)
    for child in list(paragraph):
        paragraph.remove(child)
    properties = OxmlElement("w:pPr")
    style_node = OxmlElement("w:pStyle")
    style_node.set(qn("w:val"), document.styles[style].style_id)
    properties.append(style_node)
    mark = OxmlElement("w:rPr")
    mark.append(_stamped("w:ins", ident))
    properties.append(mark)
    paragraph.append(properties)
    insertion = _stamped("w:ins", ident + 1)
    insertion.append(_run(text))
    paragraph.append(insertion)
    anchor._p.addnext(paragraph)
    return paragraph


def report_from_notes(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("Warehouse move: report", level=0)
    document.add_heading("Summary", level=1)
    document.add_paragraph(
        "The lease on the old Leeds warehouse ends on 30 June 2026. The new site in Wakefield is "
        "14 miles away. The move is quoted at 184,000 GBP against a budget of 200,000 GBP."
    )
    document.add_heading("Costs", level=1)
    rows = [
        ("Item", "Amount (GBP)"),
        ("Move, quoted by Northline", "184,000"),
        ("Wifi survey for 35 scanners", "6,500"),
        ("Lower trailers", "1,800"),
        ("Insurance in transit", "4,200"),
        ("Replacement rack (each)", "310"),
    ]
    table = document.add_table(rows=len(rows), cols=2)
    table.style = "Table Grid"
    for index, (name, amount) in enumerate(rows):
        table.cell(index, 0).text, table.cell(index, 1).text = name, amount
    document.add_paragraph("40 racks move and 12 are scrapped because of rust.")
    document.add_heading("Schedule", level=1)
    document.add_paragraph(
        "The move runs from Friday 19 June to Sunday 21 June; stock is picked again on Monday "
        "22 June."
    )
    document.add_heading("Risks", level=1)
    document.add_paragraph(
        "The loading doors at Wakefield are 3.2 m high and two trailers are 3.4 m, so lower "
        "trailers must be hired. Open question: nobody has decided whether to keep the Leeds "
        "mezzanine."
    )
    document.add_heading("Next steps", level=1)
    document.add_paragraph(
        "Dana signs the quote by 10 April; Mei books the survey; Luis updates the budget."
    )
    path = out / "warehouse_report.docx"
    document.save(path)
    return path


def memo_from_pdf(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("Memo", level=0)
    for line in (
        "To: Dana, Operations",
        "From: Finance",
        "Date: 2 March 2026",
        "Subject: Northline quote Q-2026-0412",
    ):
        document.add_paragraph(line)
    document.add_paragraph(
        "Northline quote the relocation of the Leeds warehouse to Wakefield at a total of 31,183 "
        "GBP excluding VAT. The quote is valid until 2 April 2026."
    )
    document.add_paragraph(
        "Payment: 30% deposit on acceptance, the balance 14 days after completion."
    )
    document.add_paragraph(
        "Not included: insurance of goods in transit, replacement racking and IT equipment."
    )
    document.add_paragraph("Earliest start is 15 June 2026; a weekend move needs 3 weeks' notice.")
    path = out / "northline_memo.docx"
    document.save(path)
    return path


def tracked_contract(inputs: Path, out: Path) -> Path:
    document = Document(str(inputs / "service_agreement.docx"))
    fee = next(p for p in document.paragraphs if "2,400" in p.text)
    redline(fee, "2,400", "2,650", 10)
    payment = next(p for p in document.paragraphs if "within 30 days" in p.text)
    redline(payment, "30 days", "45 days", 20)
    last = document.paragraphs[-1]
    heading = _inserted_paragraph(document, last, "Heading 2", "9. Governing law", 30)
    holder = copy.copy(last)
    holder._p = heading
    _inserted_paragraph(
        document,
        holder,
        "Normal",
        "This Agreement is governed by the laws of England and Wales.",
        40,
    )
    path = out / "service_agreement_redline.docx"
    document.save(path)
    return path


def letter_on_template(inputs: Path, out: Path) -> Path:
    document = Document(str(inputs / "letterhead.docx"))
    for line in (
        "15 June 2026",
        "Ms Ruth Okafor, Harbour Foods Ltd, 4 Dock Road, Hull HU1 2AB",
        "Dear Ms Okafor,",
        "Your order 4471 (80 pallets) will ship on 22 June 2026, five days later than promised, "
        "because a delivery of packaging arrived late. We apologise.",
        "We would like to offer a 3% discount on the invoice.",
        "Yours sincerely,",
        "Dana Whitfield, Operations Manager",
    ):
        document.add_paragraph(line, style="Letter Body")
    path = out / "letter.docx"
    document.save(path)
    return path


def table_heavy(inputs: Path, out: Path) -> Path:
    import csv
    from collections import defaultdict

    totals: dict[str, dict[str, int]] = defaultdict(dict)
    with (inputs / "sales.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            region, quarter = row["Region"], row["Quarter"]
            totals[region][quarter] = totals[region].get(quarter, 0) + int(row["Revenue"])
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    document = Document()
    document.add_heading("Regional sales review", level=0)
    table = document.add_table(rows=len(totals) + 2, cols=6)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Region"
    for column, quarter in enumerate([*quarters, "Total"], start=1):
        table.rows[0].cells[column].text = quarter
    for index, region in enumerate(totals, start=1):
        cells = table.rows[index].cells
        cells[0].text = region
        for column, quarter in enumerate(quarters, start=1):
            cells[column].text = f"{totals[region][quarter]:,}"
        cells[5].text = f"{sum(totals[region].values()):,}"
    last = table.rows[-1].cells
    last[0].text = "Total"
    for column, quarter in enumerate(quarters, start=1):
        last[column].text = f"{sum(t[quarter] for t in totals.values()):,}"
    last[5].text = f"{sum(sum(t.values()) for t in totals.values()):,}"
    document.add_paragraph(
        "South is the largest region with 84,200. Revenue grows to 75,950 in Q4."
    )
    path = out / "regional_sales_review.docx"
    document.save(path)
    return path


def mixed_language(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("新员工入职通知", level=0)
    document.add_heading("入职安排", level=1)
    document.add_paragraph("入职日期：2026年5月6日（周三），上午9:30到前台报到。")
    document.add_paragraph("部门：数据平台组 (Data Platform)，直属经理：陈静。")
    document.add_heading("设备与待遇", level=1)
    document.add_paragraph("笔记本电脑和门禁卡在第一天发放；IT 热线 8800。午餐补贴每天35元。")
    document.add_heading("试用期与培训", level=1)
    document.add_paragraph("试用期3个月，转正评估在2026年8月6日。")
    path = out / "onboarding_zh.docx"
    document.save(path)
    return path


def restructure(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("Staff handbook", level=0)
    document.add_paragraph("This handbook sets out how we work. It applies to all staff.")
    paragraph = document.add_paragraph()
    begin, instruction, end = (
        OxmlElement("w:fldChar"),
        OxmlElement("w:instrText"),
        OxmlElement("w:fldChar"),
    )
    begin.set(qn("w:fldCharType"), "begin")
    instruction.text = ' TOC \\o "1-3" \\h \\z \\u '
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instruction, end):
        run = OxmlElement("w:r")
        run.append(node)
        paragraph._p.append(run)
    sections = [
        (
            "Safety",
            [
                "Report any accident to the duty manager within one hour.",
                "Fire exits are checked every Monday morning.",
            ],
        ),
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
            "Remote work",
            [
                "Staff may work from home two days a week.",
                "The company pays a 20 GBP monthly allowance.",
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
    for title, items in sections:
        document.add_heading(title, level=1)
        for item in items:
            document.add_paragraph(item, style="List Bullet")
    document.add_heading("Contacts", level=1)
    table = document.add_table(rows=3, cols=2)
    table.style = "Table Grid"
    for row, (name, who) in enumerate(
        [("Duty manager", "ext. 201"), ("HR", "ext. 305"), ("IT desk", "ext. 410")]
    ):
        table.cell(row, 0).text, table.cell(row, 1).text = name, who
    path = out / "handbook_v2.docx"
    document.save(path)
    return path


def image_caption(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("Intake process", level=0)
    document.add_picture(str(inputs / "process.png"), width=Inches(6))
    document.add_paragraph("Figure 1: Intake process", style="Caption")
    document.add_paragraph(
        "Work moves from left to right: Receive (blue), Review (orange), then Approve (green)."
    )
    path = out / "intake_process.docx"
    document.save(path)
    return path


def _table(document: Document, rows: list[tuple[str, ...]]) -> None:
    table = document.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            table.cell(r, c).text = value


def proposal(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("Proposal: one delivery form for Northwind Logistics", level=0)
    document.add_paragraph(
        "For Priya Raman, Head of Operations. Decision by the board on 21 October 2026."
    )
    document.add_heading("The problem", level=1)
    document.add_paragraph(
        "Drivers re-key delivery notes into three systems, about 40 minutes per driver per day, "
        "and 6% of invoices had errors last quarter."
    )
    document.add_heading("Our approach", level=1)
    document.add_paragraph(
        "One Android form that works offline in the vans and feeds the warehouse system, "
        "invoicing and the customer portal, for all 140 drivers."
    )
    document.add_heading("Timeline", level=1)
    document.add_paragraph(
        "Two weeks of discovery, three 4-week build sprints, a pilot with 20 drivers in January "
        "and full rollout in February, live before 1 March 2027."
    )
    document.add_heading("Team", level=1)
    document.add_paragraph(
        "Daniel Cho (delivery lead), Ana Ruiz (Android), Tom Price (integration)."
    )
    document.add_heading("Price", level=1)
    _table(
        document,
        [
            ("Item", "Amount (GBP)"),
            ("Discovery (2 weeks)", "12,000"),
            ("Build sprints (3 x 4 weeks)", "84,000"),
            ("Pilot support (20 drivers)", "9,500"),
            ("Rollout and training (140 drivers)", "14,000"),
            ("Year-one support", "18,000"),
            ("Total", "137,500"),
        ],
    )
    document.add_heading("Risk", level=1)
    document.add_paragraph(
        "The customer portal vendor's API is undocumented; discovery confirms it first."
    )
    document.add_page_break()
    document.add_paragraph("Northwind Logistics, Leeds.")
    path = out / "proposal_northwind.docx"
    document.save(path)
    return path


def half_year_summary(inputs: Path, out: Path) -> Path:
    document = Document()
    document.add_heading("华东销售部2026年上半年工作总结", level=0)
    document.add_heading("一、主要成绩", level=1)
    document.add_paragraph(
        "上半年营收 5805 万元，完成全年目标 11000 万元的 52.8%；新客户 257 家；"
        "客户满意度从 1 月的 91.2 提升到 6 月的 94.0。"
        "新的报价系统上线后，报价周期从 3 天缩短到 1 天。"
    )
    _table(
        document,
        [
            ("月份", "营收(万元)", "新客户数", "客户满意度"),
            ("1月", "812", "34", "91.2"),
            ("2月", "705", "28", "90.5"),
            ("3月", "968", "41", "92.8"),
            ("4月", "1023", "45", "93.1"),
            ("5月", "1110", "52", "92.4"),
            ("6月", "1187", "57", "94.0"),
        ],
    )
    document.add_paragraph("2 月受春节影响营收最低（705 万元）。")
    document.add_heading("二、存在的问题", level=1)
    document.add_paragraph("苏州大客户流失 1 家，原因是交付延期；人员流动率 12%。")
    document.add_heading("三、下半年计划", level=1)
    document.add_paragraph("重点开拓南京市场；6 名新人在 8 月前完成培训；交付准时率提升到 98%。")
    path = out / "华东销售部2026年上半年工作总结.docx"
    document.save(path)
    return path


def restructure_report(inputs: Path, out: Path) -> Path:
    """Done with coscribe's own `edit_docx_structure`, as the task means it to be."""
    import shutil

    from coscribe.tools.office.document_tools import build_document_tools

    shutil.copy(inputs / "weekly_report.docx", out / "weekly_report.docx")
    tools = {tool.__name__: tool for tool in build_document_tools(out)}  # type: ignore[attr-defined]
    tools["edit_docx_structure"](
        path="weekly_report.docx",
        output_path="weekly_report_v2.docx",
        operations=[
            {"op": "delete_section", "section": "旧流程说明"},
            {"op": "move_section", "section": "问题与风险", "before": "二、项目进展"},
            {
                "op": "insert",
                "after_section": "问题与风险",
                "content": "# 三、下周计划\n\n| 工作 | 负责人 | 日期 |\n| --- | --- | --- |\n"
                "| 系统切换 | 王敏 | 6 月 20 日 |\n| 新员工培训 | 李强 | 6 月 24 日 |\n"
                "| 项目验收 | 张华 | 6 月 28 日 |",
            },
        ],
    )
    (out / "weekly_report.docx").unlink()
    return out / "weekly_report_v2.docx"


def _spec_tools(out: Path, state_dir: Path | None = None) -> dict:
    from coscribe.tools.office.document_tools import build_document_tools

    return {t.__name__: t for t in build_document_tools(out, state_dir=state_dir)}  # type: ignore[attr-defined]


def quarterly_report(inputs: Path, out: Path) -> Path:
    """Written from a spec (decision 0024), as the task means the new grammar to be used."""
    _spec_tools(out)["write_docx"](
        path="q3_report.docx",
        content=(
            "---\ntitle: Q3 operations report\nsubtitle: Harbor Freight Co.\n"
            "author: Operations\ndate: 14 October 2026\ncover: band\ntoc: true\n---\n\n"
            "# Headline figures\n\n"
            ":::stats\nOn-time delivery | 96.5% | +1.4 pt on Q2 (95.1%)\n"
            "Shipments | 128,400 | Q2: 117,900\n"
            "Cost per shipment | 41.20 USD | Q2: 43.80 USD\n"
            "Complaints | 212 | Q2: 268\n:::\n\n"
            "# Monthly shipments\n\n"
            ":::chart bar Shipments by month\n| Month | Shipments |\n| --- | --- |\n"
            "| July | 41200 |\n| August | 42600 |\n| September | 44600 |\n:::\n\n"
            "| Month | Shipments | On-time % | Cost per shipment (USD) |\n"
            "| --- | --- | --- | --- |\n| July | 41,200 | 96.0 | 41.90 |\n"
            "| August | 42,600 | 96.4 | 41.30 |\n| September | 44,600 | 97.1 | 40.40 |\n"
            "| Total | 128,400 | | |\n\n"
            "# Risk\n\n:::callout warn\nThe port strike expected in November could delay Q4 "
            "inbound containers by up to 9 days.\n:::\n\n"
            "# Next steps\n\n- Open the Rotterdam hub in January 2027.\n"
            "- Renew the carrier contract with Meridian Lines by 30 November 2026.\n"
        ),
    )
    return out / "q3_report.docx"


def figures_agree(inputs: Path, out: Path) -> Path:
    _spec_tools(out)["write_docx"](
        path="q2_sales_summary.docx",
        content=(
            "---\ntitle: Q2 regional sales summary\nfacts:\n  q1: 4,370\n  q2: 4,820\n---\n\n"
            "# Summary\n\nSales were {fact:q2} thousand USD in Q2 against {fact:q1} thousand in "
            "Q1, growth of 10.3%. East is the largest region at 1,610 thousand.\n\n"
            "| Region | Q1 | Q2 |\n| --- | --- | --- |\n| North | 1,200 | 1,350 |\n"
            "| South | 980 | 1,020 |\n| East | 1,430 | 1,610 |\n| West | 760 | 840 |\n"
            "| Total | 4,370 | 4,820 |\n\n"
            ":::chart bar Q1 and Q2 by region\n| Region | Q1 | Q2 |\n| --- | --- | --- |\n"
            "| North | 1200 | 1350 |\n| South | 980 | 1020 |\n| East | 1430 | 1610 |\n"
            "| West | 760 | 840 |\n:::\n"
        ),
    )
    return out / "q2_sales_summary.docx"


def brand_report_zh(inputs: Path, out: Path) -> Path:
    import tempfile

    from coscribe.tools.design_systems import DesignSystemStore

    state = Path(tempfile.mkdtemp())
    store = DesignSystemStore(state)
    store.update(
        store.create("Brand")["id"],
        {
            "name": "Brand",
            "colors": [{"name": "Brand red", "value": "#B00020", "note": ""}],
            "typography": {"fonts": ["Noto Sans CJK SC"], "styles": []},
        },
    )
    _spec_tools(out, state)["write_docx"](
        path="华南品牌部2026年第二季度月报.docx",
        content=(
            "---\ntitle: 华南品牌部2026年第二季度月报\nauthor: 品牌部\ncover: rule\ntoc: true\n"
            "design_system: Brand\n---\n\n# 销量\n\n"
            "门店销量从4月的3,200件增长到6月的3,900件，线上销量从1,800件增长到2,600件，"
            "6月线上销量首次占总销量的40%以上；满意度从92.5%提高到94.2%。\n\n"
            ":::chart bar 月度销量\n| 月份 | 门店销量 | 线上销量 |\n| --- | --- | --- |\n"
            "| 4月 | 3200 | 1800 |\n| 5月 | 3500 | 2100 |\n| 6月 | 3900 | 2600 |\n:::\n\n"
            "| 月份 | 门店销量 | 线上销量 | 满意度(%) |\n| --- | --- | --- | --- |\n"
            "| 4月 | 3,200 | 1,800 | 92.5 |\n| 5月 | 3,500 | 2,100 | 93.1 |\n"
            "| 6月 | 3,900 | 2,600 | 94.2 |\n\n"
            "# 风险\n\n:::callout warn\n7月起原材料涨价，预计单件成本上升约3%。\n:::\n\n"
            "# 下一步\n\n- 2026年8月15日前完成广州旗舰店改造。\n- 9月30日前上线会员小程序。\n"
        ),
    )
    return out / "华南品牌部2026年第二季度月报.docx"


SOLUTIONS = {
    "01-report-from-notes": report_from_notes,
    "02-memo-from-pdf": memo_from_pdf,
    "03-tracked-contract": tracked_contract,
    "04-letter-on-template": letter_on_template,
    "05-table-heavy": table_heavy,
    "06-mixed-language": mixed_language,
    "07-restructure": restructure,
    "08-image-caption": image_caption,
    "09-proposal": proposal,
    "10-half-year-summary": half_year_summary,
    "11-restructure-report": restructure_report,
    "12-quarterly-report": quarterly_report,
    "13-figures-agree": figures_agree,
    "14-brand-report-zh": brand_report_zh,
}
