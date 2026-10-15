"""What an approval card shows and what the audit record keeps, as tables.

Part 3 of the decision table in `test_approval_decisions.py`: once a call is decided,
`ChatSessionLG._decide_action_request` also builds the card a person sees (the arguments and,
for a document edit, a before and an after picture) and writes the record an auditor reads
(the reason, the explanation behind it, the arguments with secrets blanked). Both are checked
through the real method with a fake socket; the page renderer is replaced by a recorder, so
no LibreOffice is needed. A row changes only when the card or the record is changed on purpose.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from coscribe.conversation import edit_preview as edit_preview_module
from coscribe.runtime_lg.audit import AuditLog
from coscribe.runtime_lg.auto_review import Verdict
from tests.test_approval_decisions import (
    EXEC,
    EXTERNAL,
    LOCAL,
    _decide,
    _session,
    _Socket,
    _veto,
    _write_exec_rule,
)

CARD_KEYS = {
    "type",
    "id",
    "tool_name",
    "arguments",
    "before_preview",
    "after_preview",
    "reviewer_note",
}


class _Toolkit:
    """Stands in for a document toolkit: `edit` changes the copy it is given, and `_private`
    is what a preview must never call."""

    calls: list[dict[str, Any]] = []
    fail = False

    def __init__(self, root: str, **kwargs: Any) -> None:
        self.root = Path(root)

    def edit(self, **kwargs: Any) -> None:
        _Toolkit.calls.append({**kwargs, "root": self.root})
        if _Toolkit.fail:
            raise RuntimeError("the edit cannot run")
        (self.root / kwargs["path"]).write_bytes(b"after")

    def _private(self, **kwargs: Any) -> None:
        raise AssertionError("a private helper is never previewed")


@pytest.fixture
def renders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[tuple[bytes, int]]:
    """The pages rendered, as (the file's bytes at that moment, the page number)."""
    pages: list[tuple[bytes, int]] = []

    def render(path: Path, state_dir: Path, page: int) -> tuple[str, str]:
        pages.append((Path(path).read_bytes(), page))
        return (f"picture-{len(pages)}.png", "ok")

    monkeypatch.setattr(edit_preview_module, "render_single_page_preview", render)
    monkeypatch.setitem(edit_preview_module.PREVIEWABLE_TOOLKITS_BY_EXTENSION, ".docx", _Toolkit)
    monkeypatch.setitem(edit_preview_module.PREVIEWABLE_TOOLKITS_BY_EXTENSION, ".xlsx", _Toolkit)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    _Toolkit.calls, _Toolkit.fail = [], False
    return pages


@dataclass
class PreviewRow:
    """One gated call and the pictures its approval card carries."""

    tool: str
    args: dict[str, Any]
    before: str | None
    after: str | None
    rendered: int  # pages rendered, before and after together
    page: int = 1  # the page both pictures are of
    file: str | None = "report.docx"  # created in the workspace first
    outside: str | None = None  # created next to the workspace, where a path must not reach
    fails: bool = False  # the dry run raises
    attended: bool = True


PREVIEW_ROWS: dict[str, PreviewRow] = {
    "a_document_edit_shows_before_and_after": PreviewRow(
        "edit", {"path": "report.docx", "text": "x"}, "picture-1.png", "picture-2.png", 2
    ),
    "a_workbook_edit_is_previewed_too": PreviewRow(
        "edit",
        {"path": "sheet.xlsx"},
        "picture-1.png",
        "picture-2.png",
        2,
        file="sheet.xlsx",
    ),
    "the_extension_is_matched_in_any_case": PreviewRow(
        "edit", {"path": "REPORT.DOCX"}, "picture-1.png", "picture-2.png", 2, file="REPORT.DOCX"
    ),
    "a_slide_argument_picks_the_page": PreviewRow(
        "edit", {"path": "report.docx", "slide": 3}, "picture-1.png", "picture-2.png", 2, page=3
    ),
    "a_slide_that_is_not_positive_falls_back_to_page_one": PreviewRow(
        "edit", {"path": "report.docx", "slide": 0}, "picture-1.png", "picture-2.png", 2
    ),
    "a_slide_that_is_not_a_number_falls_back_to_page_one": PreviewRow(
        "edit", {"path": "report.docx", "slide": "2"}, "picture-1.png", "picture-2.png", 2
    ),
    "a_failed_dry_run_shows_the_before_only": PreviewRow(
        "edit", {"path": "report.docx"}, "picture-1.png", None, 1, fails=True
    ),
    "a_file_that_does_not_exist_has_no_preview": PreviewRow(
        "edit", {"path": "missing.docx"}, None, None, 0, file=None
    ),
    "a_path_outside_the_workspace_has_no_preview": PreviewRow(
        "edit", {"path": "../outside.docx"}, None, None, 0, file=None, outside="outside.docx"
    ),
    "a_path_that_is_not_text_has_no_preview": PreviewRow(
        "edit", {"path": 3}, None, None, 0, file=None
    ),
    "a_call_without_a_path_has_no_preview": PreviewRow("edit", {"text": "x"}, None, None, 0),
    "an_extension_without_a_toolkit_has_no_preview": PreviewRow(
        "edit", {"path": "notes.txt"}, None, None, 0, file="notes.txt"
    ),
    "a_private_method_is_never_previewed": PreviewRow(
        "_private", {"path": "report.docx"}, None, None, 0
    ),
    "a_name_that_is_not_a_method_is_never_previewed": PreviewRow(
        "nothing_like_it", {"path": "report.docx"}, None, None, 0
    ),
    "nobody_to_show_it_to_means_no_picture_is_built": PreviewRow(
        "edit", {"path": "report.docx"}, None, None, 0, attended=False
    ),
}


@pytest.mark.parametrize("name", sorted(PREVIEW_ROWS))
async def test_the_pictures_on_an_approval_card(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    renders: list[tuple[bytes, int]],
) -> None:
    row = PREVIEW_ROWS[name]
    session = _session(tmp_path, monkeypatch)
    session._gated_tool_risks[row.tool] = "WRITE_LOCAL"
    if row.file is not None:
        (tmp_path / "workspace" / row.file).write_bytes(b"before")
    if row.outside is not None:
        (tmp_path / row.outside).write_bytes(b"before")
    _Toolkit.fail = row.fails
    socket = _Socket(row.attended)

    result = await _decide(session, row.tool, socket, answer=False, args=row.args)

    assert result["type"] == "reject"
    assert [page for _, page in renders] == [row.page] * row.rendered
    assert [content for content, _ in renders] == [b"before", b"after"][: row.rendered]
    cards = [m for m in socket.sent if m["type"] == "approval_required"]
    if not row.attended:
        assert cards == []
        return
    assert [(c["before_preview"], c["after_preview"]) for c in cards] == [(row.before, row.after)]
    if row.file is not None:
        assert (tmp_path / "workspace" / row.file).read_bytes() == b"before"
    assert list((tmp_path / "tmp").iterdir()) == []


async def test_the_dry_run_gets_the_same_arguments_on_a_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, renders: list[tuple[bytes, int]]
) -> None:
    session = _session(tmp_path, monkeypatch)
    session._gated_tool_risks["edit"] = "WRITE_LOCAL"
    (tmp_path / "workspace" / "sub").mkdir()
    (tmp_path / "workspace" / "sub" / "report.docx").write_bytes(b"before")
    args = {"path": "sub/report.docx", "text": "new", "size": 12}

    await _decide(session, "edit", _Socket(True), answer=False, args=args)

    [call] = _Toolkit.calls
    assert {k: v for k, v in call.items() if k != "root"} == {**args, "path": "report.docx"}
    assert call["root"] != tmp_path / "workspace"


# ---------------------------------------------------------------------------
# The card itself
# ---------------------------------------------------------------------------


async def test_the_card_carries_the_call_and_its_reviewer_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    session.auto_mode = True

    async def reviewer(
        tool: str, args: dict[str, Any], *, delegated_task: str = ""
    ) -> Verdict | None:
        return None

    monkeypatch.setattr(session, "_auto_review", reviewer)
    socket = _Socket(True)
    args = {"path": "a.txt", "content": "hi", "api_key": "kept on the card"}

    await _decide(session, LOCAL, socket, answer=True, args=args)

    [card] = [m for m in socket.sent if m["type"] == "approval_required"]
    assert set(card) == CARD_KEYS
    assert card["tool_name"] == LOCAL
    assert card["arguments"] == args
    assert card["before_preview"] is None and card["after_preview"] is None
    assert "gave no answer" in card["reviewer_note"]
    assert isinstance(card["id"], str) and card["id"]


async def test_two_cards_have_different_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    socket = _Socket(True)

    await _decide(session, LOCAL, socket, answer=True, args={"path": "a.txt"})
    await _decide(session, LOCAL, socket, answer=True, args={"path": "b.txt"})

    ids = [m["id"] for m in socket.sent if m["type"] == "approval_required"]
    assert len(ids) == 2 and ids[0] != ids[1]


# ---------------------------------------------------------------------------
# The audit record
# ---------------------------------------------------------------------------

SECRET = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4"


@dataclass
class RecordCase:
    """One decision and the explanation its audit record keeps."""

    tool: str
    reason: str
    detail: str | None  # the record's detail, exactly
    decision: str = "reject"
    veto: str | None = None
    plan: bool = False
    exec_rule: str | None = None
    preapproved: bool = False
    accept_edits: bool = False
    run_mode: str | None = None
    attended: bool = True
    verdict: Verdict | None = None
    human: bool | None = None


UNATTENDED = "No one is available to approve this -- this is an unattended run."
PLAN = (
    "Plan mode is active (read-only). Note this step with task_create instead; the user needs "
    "to turn plan mode off before it can run."
)

RECORD_CASES: dict[str, RecordCase] = {
    "a_hook_veto_keeps_the_hooks_message": RecordCase(
        LOCAL, "hook_veto", "needs a ticket first", veto="needs a ticket first"
    ),
    "a_hook_veto_keeps_the_message_with_secrets_blanked": RecordCase(
        LOCAL, "hook_veto", "token [REDACTED] is not allowed", veto=f"token {SECRET} is not allowed"
    ),
    "plan_mode_keeps_its_explanation": RecordCase(LOCAL, "plan_mode", PLAN, plan=True),
    "a_forbidden_script_keeps_the_rules_justification": RecordCase(
        EXEC, "exec_policy", "by the policy", exec_rule="forbidden"
    ),
    "an_allowed_script_keeps_the_rules_justification": RecordCase(
        EXEC, "exec_policy", "by the policy", decision="approve", exec_rule="allow"
    ),
    "the_reviewers_reason_is_kept_for_an_allow": RecordCase(
        LOCAL,
        "auto_review",
        "only the folder",
        decision="approve",
        verdict=Verdict(True, "only the folder"),
    ),
    "the_reviewers_reason_is_kept_for_a_block": RecordCase(
        LOCAL,
        "auto_review_block",
        "reaches out",
        verdict=Verdict(False, "reaches out"),
        human=False,
    ),
    "unattended_keeps_why_nobody_was_asked": RecordCase(
        LOCAL, "unattended", UNATTENDED, attended=False
    ),
    "a_person_approving_needs_no_explanation": RecordCase(
        EXTERNAL, "human", None, decision="approve", human=True
    ),
    "a_person_refusing_needs_no_explanation": RecordCase(EXTERNAL, "human", None, human=False),
    "preapproved_needs_no_explanation": RecordCase(
        LOCAL, "preapproved", None, decision="approve", preapproved=True
    ),
    "accept_edits_needs_no_explanation": RecordCase(
        LOCAL, "accept_edits", None, decision="approve", accept_edits=True
    ),
    "a_run_that_skips_approval_needs_no_explanation": RecordCase(
        EXEC, "approval_mode_skip", None, decision="approve", run_mode="skip"
    ),
}


@pytest.mark.parametrize("name", sorted(RECORD_CASES))
async def test_the_audit_record_for_one_decision(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = RECORD_CASES[name]
    session = _session(tmp_path, monkeypatch)
    session.plan_mode = case.plan
    session.accept_edits = case.accept_edits
    session.run_approval_mode = case.run_mode
    session.preapproved_tools = frozenset({case.tool}) if case.preapproved else frozenset()
    session.auto_mode = case.verdict is not None

    async def reviewer(
        tool: str, args: dict[str, Any], *, delegated_task: str = ""
    ) -> Verdict | None:
        return case.verdict

    monkeypatch.setattr(session, "_auto_review", reviewer)
    _write_exec_rule(session, case.exec_rule)
    _veto(monkeypatch, session, case.veto)
    args = {"script": f"print('{SECRET}')", "path": "a.txt", "password": "hunter2", "size": 3}

    await _decide(session, case.tool, _Socket(case.attended), answer=case.human, args=args)

    entries = AuditLog(session.settings.state_dir).read_all()
    assert [e.reason for e in entries][-1] == case.reason
    entry = entries[-1]
    assert entry.detail == case.detail
    assert entry.decision == case.decision
    assert entry.thread_id == "t1"
    assert entry.tool_name == case.tool
    assert entry.arguments == {
        "script": "print('[REDACTED]')",
        "path": "a.txt",
        "password": "[REDACTED]",
        "size": 3,
    }
    assert datetime.fromisoformat(entry.timestamp).tzinfo is not None


async def test_a_stop_and_an_ungated_call_leave_no_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    _veto(monkeypatch, session, None)

    await _decide(session, "read_file", _Socket(True), args={"path": "a.txt"})
    session._stop_requested = True
    await _decide(session, LOCAL, _Socket(True), args={"path": "a.txt"})

    assert AuditLog(session.settings.state_dir).read_all() == []


async def test_the_raw_arguments_are_not_changed_by_redaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path, monkeypatch)
    args = {"path": "a.txt", "token": "abc"}
    socket = _Socket(True)

    await _decide(session, LOCAL, socket, answer=True, args=args)

    assert args == {"path": "a.txt", "token": "abc"}
