"""Taking data off a page: a table or list to a CSV or as text, and the page as a PDF."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

from coscribe.runtime import get_tool_metadata
from coscribe.tools._workspace import WorkspaceScope
from coscribe.tools.web.browser import BrowserHost, build_browser_tools

_TABLE = {
    "kind": "table",
    "header": ["Invoice No.", "Amount", "Note"],
    "rows": [["INV-1", "-12.5", '=HYPERLINK("http://x")'], ["INV-2", "30", "+1 call"]],
    "pages": 3,
    "stopped": "end",
    "tab": {"id": 1, "title": "Invoices", "url": "https://erp.example/"},
}


class _Host(BrowserHost):
    def __init__(self, replies: dict[str, dict[str, Any]]) -> None:
        super().__init__()
        self.replies = replies
        self.calls: list[tuple[str, dict[str, Any], float]] = []

    def call(
        self, action: str, args: dict[str, Any], thread_id: str, timeout: float = 30
    ) -> dict[str, Any]:
        self.calls.append((action, args, timeout))
        return self.replies[action]


def _tools(host: BrowserHost, root: Path | None = None) -> dict[str, Any]:
    scope = WorkspaceScope(root) if root is not None else None
    return {t.__name__: t for t in build_browser_tools("t1", host, scope=scope)}


def test_a_table_without_a_path_comes_back_as_rows(tmp_path: Path) -> None:
    host = _Host({"save_table": {**_TABLE, "pages": 1}})
    text = _tools(host, tmp_path)["browser_save_table"]("Invoice No.")
    assert text.startswith("Read 2 rows:\nInvoice No.\tAmount\tNote\nINV-1\t-12.5")
    action, args, _ = host.calls[0]
    assert action == "save_table"
    assert (args["table"], args["max_pages"], args["scroll"]) == ("Invoice No.", 1, False)
    assert not list(tmp_path.iterdir())


def test_a_table_across_pages_is_saved_as_a_csv_excel_reads(tmp_path: Path) -> None:
    host = _Host({"save_table": _TABLE})
    tools = _tools(host, tmp_path)
    result = tools["browser_save_table"](
        "Invoice No.", path="data/invoices", next_page='button "Next"', max_pages=5
    )

    assert result["file"] == "data/invoices.csv" and result["rows"] == 2
    assert result["message"].startswith("Saved 2 rows from 3 pages to data/invoices.csv.")
    raw = (tmp_path / "data" / "invoices.csv").read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    lines = raw.decode("utf-8-sig").splitlines()
    assert lines[0] == "Invoice No.,Amount,Note"
    # A planted formula stays text; a negative number stays a number.
    assert lines[1] == 'INV-1,-12.5,"\'=HYPERLINK(""http://x"")"'
    assert lines[2] == "INV-2,30,'+1 call"
    assert host.calls[0][1]["next_page"] == 'button "Next"'
    assert host.calls[0][2] > 30 * 5

    again = tools["browser_save_table"]("Invoice No.", path="data/invoices.csv")
    assert again["file"] == "data/invoices (1).csv"


def test_stopping_at_max_pages_says_there_may_be_more(tmp_path: Path) -> None:
    host = _Host({"save_table": {**_TABLE, "stopped": "max_pages"}})
    text = _tools(host, tmp_path)["browser_save_table"](scroll=True, max_pages=3)
    assert "stopped at max_pages=3, so there may be more" in text


def test_save_table_refuses_unclear_arguments(tmp_path: Path) -> None:
    host = _Host({"save_table": _TABLE})
    tools = _tools(host, tmp_path)
    for kwargs in ({"next_page": "Next", "scroll": True}, {"max_pages": 0}, {"max_pages": 101}):
        with pytest.raises(ValueError):
            tools["browser_save_table"](**kwargs)
    with pytest.raises(ValueError, match="Saving files"):
        _tools(host)["browser_save_table"](path="a.csv")
    assert not host.calls


def test_the_page_is_saved_as_a_pdf(tmp_path: Path) -> None:
    host = _Host({"save_pdf": {"pdf": base64.b64encode(b"%PDF-1.7").decode()}})
    result = _tools(host, tmp_path)["browser_save_pdf"]("reports/page", landscape=True)
    assert result["file"] == "reports/page.pdf"
    assert (tmp_path / "reports" / "page.pdf").read_bytes() == b"%PDF-1.7"
    assert host.calls[0][1]["landscape"] is True


def test_saving_writes_local_files_only() -> None:
    tools = _tools(_Host({}))
    risks = {name: get_tool_metadata(tools[name]).risk_category for name in tools}
    assert risks["browser_save_table"] == risks["browser_save_pdf"] == "WRITE_LOCAL"


async def test_a_saved_workflow_collects_a_table_and_uses_the_file(tmp_path: Path) -> None:
    pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")
    from langgraph.checkpoint.memory import InMemorySaver

    from coscribe.workflow_spec import parse_workflow
    from coscribe.workflows.engine import StepContext, WorkflowRun

    host = _Host({"save_table": _TABLE})
    read: list[str] = []
    tools: dict[str, Any] = {
        t.__name__: t
        for t in build_browser_tools(
            "run-1", host, scope=WorkspaceScope(tmp_path), saved_workflow=True
        )
    }
    tools["read_file"] = lambda path: read.append(path) or "ok"
    ctx = StepContext(tools=tools, workspace_root=tmp_path, state_dir=tmp_path / "state",
                      make_model=lambda name: None)  # fmt: skip
    workflow = parse_workflow(
        {
            "steps": [
                {"id": "collect", "kind": "tool", "title": "Collect the invoices",
                 "tool": "browser_save_table", "save_as": "invoices",
                 "args": {"table": "Invoice No.", "next_page": 'button "Next"',
                          "path": "invoices.csv"}},
                {"id": "use", "kind": "tool", "title": "Read them", "tool": "read_file",
                 "args": {"path": "{{invoices.file}}"}},
            ]
        }
    )  # fmt: skip

    outcome = await WorkflowRun(workflow, ctx, InMemorySaver(), "run-1", lambda record: None).start(
        {}
    )

    assert outcome.status == "completed", outcome
    assert read == ["invoices.csv"]
    assert host.calls[0][1]["saved_workflow"] is True
