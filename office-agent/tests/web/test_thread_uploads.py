# ruff: noqa: E402
"""Web tests: uploads, previews and the slide shapes endpoint."""

import re
from pathlib import Path

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from pptx import Presentation

from coscribe.web.routes import files as files_routes

from .helpers import (
    FakeToolCallingChatModel,
    _client_lg,
    _write_test_deck,
)


def test_upload_writes_file_to_workspace_and_returns_relative_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("report.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == ".coscribe/uploads/documents/report.pdf"
    assert body["bytes_written"] == len(b"%PDF-1.4 fake content")
    saved = tmp_path / "workspace" / ".coscribe" / "uploads" / "documents" / "report.pdf"
    assert saved.read_bytes() == b"%PDF-1.4 fake content"


def test_an_upload_and_a_slide_overlay_use_the_conversations_own_folder_lg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real bug: with a folder chosen for a conversation, an attached file
    landed in the app's default workspace -- the path the model was given
    pointed nowhere in its folder -- and the click-a-shape overlay couldn't
    find a deck that lived there."""
    from pptx import Presentation

    chosen = tmp_path / "project-folder"
    chosen.mkdir()
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[5])
    prs.save(str(chosen / "deck.pptx"))
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        env = client.post("/api/environments", json={"name": "Own", "folders": [str(chosen)]})
        with client.websocket_connect("/ws/t_own_folder") as ws:
            ws.receive_json()
            ws.receive_json()
            ws.send_json({"type": "set_environment", "environment": env.json()["id"]})
            ws.receive_json()
            uploaded = client.post(
                "/api/upload",
                data={"thread_id": "t_own_folder"},
                files={"file": ("brief.txt", b"hello", "text/plain")},
            ).json()
            shapes = client.get(
                "/api/pptx-shapes",
                params={"path": "deck.pptx", "slide": 1, "thread_id": "t_own_folder"},
            )
            without_thread = client.get(
                "/api/pptx-shapes", params={"path": "deck.pptx", "slide": 1}
            )

    assert uploaded["path"] == ".coscribe/uploads/documents/brief.txt"
    assert (chosen / uploaded["path"]).read_bytes() == b"hello"
    assert not (tmp_path / "workspace" / ".coscribe").exists()
    assert shapes.status_code == 200 and shapes.json()["slide_width_in"] > 0
    assert without_thread.status_code == 400


def test_upload_auto_renames_on_name_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        first = client.post("/api/upload", files={"file": ("notes.txt", b"first", "text/plain")})
        second = client.post("/api/upload", files={"file": ("notes.txt", b"second", "text/plain")})

    assert first.json()["path"] == ".coscribe/uploads/documents/notes.txt"
    assert second.json()["path"] == ".coscribe/uploads/documents/notes (1).txt"
    workspace = tmp_path / "workspace"
    assert (workspace / first.json()["path"]).read_bytes() == b"first"
    assert (workspace / second.json()["path"]).read_bytes() == b"second"


def test_upload_sanitizes_path_traversal_attempt_in_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/upload", files={"file": ("../../evil.txt", b"data", "text/plain")}
        )

    assert response.status_code == 200
    assert response.json()["path"] == ".coscribe/uploads/documents/evil.txt"
    assert (tmp_path / "workspace" / response.json()["path"]).read_bytes() == b"data"
    assert not (tmp_path / "evil.txt").exists()


def test_each_kind_of_upload_has_its_own_folder_and_a_pasted_picture_a_dated_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:

        def upload(name: str, **data: str) -> str:
            sent = client.post("/api/upload", data=data, files={"file": (name, b"x")})
            return str(sent.json()["path"])

        paths = [upload(n) for n in ("Photo.JPG", "sales.xlsx", "deck.pptx", "tool.exe", "..")]
        pasted = upload("image.png", pasted="true")

    assert paths == [
        ".coscribe/uploads/images/Photo.JPG",
        ".coscribe/uploads/data/sales.xlsx",
        ".coscribe/uploads/documents/deck.pptx",
        ".coscribe/uploads/other/tool.exe",
        ".coscribe/uploads/other/upload",
    ]
    assert re.fullmatch(
        r"\.coscribe/uploads/screenshots/screenshot-\d{4}-\d\d-\d\d-\d{6}\.png", pasted
    )


def test_an_upload_to_a_folder_that_cant_be_written_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        (tmp_path / "workspace").mkdir(exist_ok=True)
        (tmp_path / "workspace" / ".coscribe").write_text("a file where the folder would be")
        refused = client.post("/api/upload", files={"file": ("a.txt", b"x")})

    assert refused.status_code == 409
    assert "can't be written" in refused.json()["error"]


def test_upload_rejects_oversized_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(files_routes, "MAX_UPLOAD_BYTES", 10)
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.post(
            "/api/upload", files={"file": ("big.txt", b"0123456789 -- too big", "text/plain")}
        )

    assert response.status_code == 413
    assert not (tmp_path / "workspace" / ".coscribe").exists()


def test_get_preview_serves_an_existing_preview_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    previews_dir = tmp_path / "state" / "previews"
    previews_dir.mkdir(parents=True)
    name = "0123456789abcdef0123456789abcdef.png"
    (previews_dir / name).write_bytes(b"\x89PNG\r\n\x1a\n fake png bytes")

    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get(f"/api/previews/{name}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG\r\n\x1a\n fake png bytes"


def test_get_preview_404s_for_unknown_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/previews/0123456789abcdef0123456789abcdef.png")

    assert response.status_code == 404


def test_get_preview_rejects_path_traversal_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proves the name-shape check, not just a missing-file 404 -- a name
    # that doesn't match render_thumbnail's uuid4().hex pattern is rejected
    # before any filesystem lookup, so it can never escape state_dir/previews/.
    secret = tmp_path / "state" / "secret.txt"
    secret.parent.mkdir(parents=True)
    secret.write_text("do not serve me")

    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/previews/..%2Fsecret.txt")

    assert response.status_code == 404


def test_get_pptx_shapes_returns_shapes_and_slide_dimensions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Backs the click-a-shape-in-the-preview feature (ChatLog.tsx's
    PptxShapeOverlay) -- a plain UI-facing REST read, not a tool call."""
    _write_test_deck(tmp_path / "workspace")

    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/pptx-shapes", params={"path": "deck.pptx", "slide": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["slide"] == 1
    assert body["shape_count"] == 1
    assert body["slide_width_in"] > 0
    assert body["slide_height_in"] > 0
    [shape] = body["shapes"]
    assert shape["index"] == 0
    assert shape["left_in"] == pytest.approx(1.0)
    assert shape["top_in"] == pytest.approx(1.0)
    assert shape["width_in"] == pytest.approx(2.0)
    assert shape["height_in"] == pytest.approx(1.0)
    assert shape["text_preview"] == "hello"


def test_get_pptx_shapes_400s_for_a_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/pptx-shapes", params={"path": "nope.pptx", "slide": 1})

    assert response.status_code == 400


def test_get_pptx_shapes_400s_for_an_out_of_range_slide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_test_deck(tmp_path / "workspace")

    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/pptx-shapes", params={"path": "deck.pptx", "slide": 5})

    assert response.status_code == 400


def test_get_pptx_shapes_400s_for_a_path_outside_the_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside.pptx"
    Presentation().save(str(outside))

    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        response = client.get("/api/pptx-shapes", params={"path": str(outside), "slide": 1})

    assert response.status_code == 400


def test_an_attached_pdf_can_be_previewed_page_by_page_and_nothing_else_can(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for number in (1, 2):
        pdf.drawString(100, 700, f"page {number}")
        pdf.showPage()
    pdf.save()

    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        uploaded = client.post(
            "/api/upload", files={"file": ("cv.pdf", buffer.getvalue(), "application/pdf")}
        ).json()
        text = client.post("/api/upload", files={"file": ("a.txt", b"hi", "text/plain")}).json()
        info = client.get("/api/attachment/pdf", params={"path": uploaded["path"]})
        page = client.get(
            "/api/attachment/pdf/page", params={"path": uploaded["path"], "page": 2, "width": 300}
        )
        past_end = client.get(
            "/api/attachment/pdf/page", params={"path": uploaded["path"], "page": 3}
        )
        not_pdf = client.get("/api/attachment/pdf", params={"path": text["path"]})
        outside = client.get("/api/attachment/pdf", params={"path": "../../etc/passwd"})

    assert info.json() == {"pages": 2}
    assert page.headers["content-type"] == "image/png" and page.content.startswith(b"\x89PNG")
    assert past_end.status_code == 404
    assert not_pdf.status_code == 404
    assert outside.status_code in (400, 404)


def test_xlsx_preview_reads_cells_drawings_and_scopes_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import base64
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference
    from openpyxl.drawing.image import Image
    from openpyxl.styles import PatternFill

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = workspace / "quotes.xlsx"
    book = Workbook()
    main = book.active
    assert main is not None
    main.title = "报价明细"
    main.append(["Vendor", "Price", "Total"])
    main.append(["Pine", 12, "=B2*2"])
    main["B2"].number_format = "0.00"
    main["B2"].fill = PatternFill("solid", fgColor="DCEBFA")
    main.merge_cells("A4:C4")
    main.freeze_panes = "B2"
    main.row_dimensions[3].hidden = True
    summary = book.create_sheet("Summary")
    summary["A1"] = "Yearly"
    book.create_sheet("Hidden").sheet_state = "hidden"
    chart = BarChart()
    chart.title = "Prices"
    chart.add_data(Reference(main, min_col=2, min_row=2))
    chart.set_categories(Reference(main, min_col=1, min_row=2))
    summary.add_chart(chart, "D3")
    pixel = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+yWQ0AAAAASUVORK5CYII="
    )
    summary.add_image(Image(BytesIO(pixel)), "B10")
    book.save(path)
    original = path.read_bytes()
    stamp = path.stat().st_mtime_ns
    (tmp_path / "outside.xlsx").write_bytes(original)
    (workspace / "broken.xlsx").write_bytes(b"not a workbook")
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        preview = client.post("/api/attachment/xlsx", params={"path": path.name})
        chart_sheet = client.post(
            "/api/attachment/xlsx", params={"path": path.name, "sheet": "Summary"}
        )
        hidden = client.post("/api/attachment/xlsx", params={"path": path.name, "sheet": "Hidden"})
        denied = client.post("/api/attachment/xlsx", params={"path": "../outside.xlsx"})
        corrupt = client.post("/api/attachment/xlsx", params={"path": "broken.xlsx"})

    assert preview.status_code == chart_sheet.status_code == 200
    assert preview.json()["sheets"] == ["报价明细", "Summary"]
    sheet = preview.json()["sheet"]
    assert sheet["freeze"] == [1, 1]
    assert sheet["rows"] == [[3, 3, 0]]
    assert sheet["merges"] == [[4, 1, 4, 3]]
    price, formula = [item for item in sheet["cells"] if item[0] == 2 and item[1] >= 2]
    assert price[2:4] == ["12.00", "12"]
    assert sheet["styles"][str(price[4])]["background"] == "#DCEBFA"
    assert formula[2:4] == ["", "=B2*2"]
    plot, image = chart_sheet.json()["sheet"]["drawings"]
    assert plot["labels"] == ["Pine"]
    assert plot["series"] == [[12.0]]
    assert plot["origin"] == [3, 4, 0, 0]
    assert image["src"] == "data:image/png;base64," + base64.b64encode(pixel).decode()
    assert hidden.json()["sheet"] is None
    assert denied.status_code == 403
    assert corrupt.status_code == 422
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == stamp


def test_xlsx_preview_rejects_oversized_merged_ranges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from io import BytesIO
    from zipfile import ZipFile

    from openpyxl import Workbook

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    packed = BytesIO()
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.merge_cells("A1:B2")
    book.save(packed)
    with (
        ZipFile(packed) as source,
        ZipFile(workspace / "merges.xlsx", "w") as output,
    ):
        for member in source.namelist():
            xml = source.read(member).replace(
                b'<mergeCell ref="A1:B2"', b'<mergeCell ref="A1:XFD1048576"'
            )
            output.writestr(member, xml)
    with _client_lg(tmp_path, monkeypatch, FakeToolCallingChatModel(responses=[])) as client:
        response = client.post("/api/attachment/xlsx", params={"path": "merges.xlsx"})
    assert response.status_code == 413


def test_xlsx_preview_shows_dates_in_their_number_format(tmp_path: Path) -> None:
    from datetime import date, datetime

    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference

    from coscribe.web import spreadsheet_drawings, spreadsheet_preview

    path = tmp_path / "dates.xlsx"
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    shown_as = [
        (datetime(2026, 11, 5, 14, 7, 9), "yyyy-mm-dd"),
        (datetime(2026, 11, 5, 14, 7, 9), "h:mm AM/PM"),
        (date(2026, 3, 1), "mmm d, yyyy"),
        (datetime(2026, 1, 2), 'yyyy"年"m"月"d"日"'),
        (datetime(2026, 1, 2, 9, 30), "General"),
    ]
    for row, (value, fmt) in enumerate(shown_as, start=1):
        sheet.cell(row, 1, value).number_format = fmt
        sheet.cell(row, 2, row * 10)
    chart = LineChart()
    chart.add_data(Reference(sheet, min_col=2, min_row=1, max_row=5))
    sheet.add_chart(chart, "D2")
    book.save(path)

    preview = spreadsheet_preview.read_spreadsheet(path, None)

    shown = {cell[0]: cell[2] for cell in preview["sheet"]["cells"] if cell[1] == 1}
    assert shown == {
        1: "2026-11-05",
        2: "2:07 PM",
        3: "Mar 1, 2026",
        4: "2026年1月2日",
        5: "46024.39583",  # Excel too shows a General date as its serial number
    }
    assert spreadsheet_drawings.chart_references(sheet) == {"Sheet"}
    (line,) = preview["sheet"]["drawings"]
    assert line["plot"] == "line"
    assert line["series"] == [[10.0, 20.0, 30.0, 40.0, 50.0]]


def test_word_preview_uses_a_scoped_copy_and_reuses_the_saved_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    from docx import Document
    from reportlab.pdfgen import canvas

    from coscribe.web import word_preview

    opened: list[Path] = []

    def build_preview_converter(folder: Path, *, state_dir: Path):
        assert state_dir == tmp_path / "state"

        def convert(path: str, to_format: str, output_path: str) -> None:
            assert to_format == "pdf"
            snapshot = folder / path
            opened.append(snapshot)
            result = canvas.Canvas(str(folder / output_path))
            result.drawString(50, 50, Document(snapshot).paragraphs[0].text)
            result.save()

        return [convert]

    def docx(text: str) -> bytes:
        data = io.BytesIO()
        document = Document()
        document.add_paragraph(text)
        document.save(data)
        return data.getvalue()

    monkeypatch.setattr(word_preview, "build_convert_tools", build_preview_converter)
    original = docx("First version")
    fake_model = FakeToolCallingChatModel(responses=[])
    with _client_lg(tmp_path, monkeypatch, fake_model) as client:
        uploaded = client.post(
            "/api/upload",
            data={"thread_id": "chat"},
            files={"file": ("review.docx", original)},
        ).json()
        source = tmp_path / "workspace" / uploaded["path"]
        url = "/api/attachment/docx"
        params = {"path": uploaded["path"], "thread_id": "chat"}
        outside = tmp_path / "outside.docx"
        outside.write_bytes(original)
        assert client.post(url, params={**params, "path": str(outside)}).status_code == 403
        assert client.get(url, params=params).status_code == 405
        assert client.head(url, params=params).status_code == 200
        assert opened == []
        first = client.post(url, params=params)
        assert first.status_code == 200
        assert first.content.startswith(b"%PDF")
        assert first.headers["cache-control"] == "no-store"
        assert client.post(url, params=params).content == first.content
        assert len(opened) == 1
        assert opened[0] != source and not opened[0].exists()
        assert source.read_bytes() == original
        source.write_bytes(docx("A different saved version"))
        assert client.head(url, params=params).headers["etag"] != first.headers["etag"]
        assert client.post(url, params=params).content != first.content
        assert len(opened) == 2
        source.write_bytes(b"Not a Word package")
        assert "damaged or password-protected" in client.post(url, params=params).json()["error"]
        assert len(opened) == 2
        assert not list(source.parent.glob("*.pdf"))

        def cannot_convert(*args, **kwargs) -> None:
            raise ValueError("Office error in /local/private/temp/preview.pdf")

        monkeypatch.setattr(
            word_preview, "build_convert_tools", lambda *args, **kwargs: [cannot_convert]
        )
        source.write_bytes(docx("A version the engine refuses"))
        failed = client.post(url, params=params)
        assert failed.status_code == 422
        assert "Couldn't prepare a Word preview" in failed.json()["error"]
        assert "/local/private" not in failed.text
