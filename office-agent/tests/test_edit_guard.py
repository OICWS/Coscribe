"""The edit guard: a write tool does not run on a file the person changed since the model last
read or wrote it."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain_core.messages import ToolMessage

from coscribe.runtime_lg.edit_guard import EditGuardMiddleware


def _call(name: str, path: str, **args: Any) -> SimpleNamespace:
    return SimpleNamespace(tool_call={"id": "c1", "name": name, "args": {"path": path, **args}})


def _guard(root: Path) -> tuple[EditGuardMiddleware, list[str]]:
    ran: list[str] = []
    guard = EditGuardMiddleware(lambda p: root / p, {"edit_docx_review"})

    def handler(request: Any) -> ToolMessage:
        ran.append(request.tool_call["name"])
        return ToolMessage(content="ok", tool_call_id="c1", name=request.tool_call["name"])

    guard.handler = handler  # type: ignore[attr-defined]
    return guard, ran


def _run(guard: EditGuardMiddleware, request: Any) -> Any:
    return guard.wrap_tool_call(request, guard.handler)  # type: ignore[attr-defined]


def test_a_write_after_the_person_edited_is_refused_until_the_file_is_read_again(tmp_path):
    (tmp_path / "a.docx").write_bytes(b"one")
    guard, ran = _guard(tmp_path)
    _run(guard, _call("read_docx_review", "a.docx"))

    (tmp_path / "a.docx").write_bytes(b"one, edited in the app")
    refused = _run(guard, _call("edit_docx_review", "a.docx"))
    assert refused.status == "error" and "read it again" in refused.content.lower()
    assert ran == ["read_docx_review"]

    _run(guard, _call("read_docx_review", "a.docx"))
    done = _run(guard, _call("edit_docx_review", "a.docx"))
    assert done.content == "ok" and ran == ["read_docx_review"] * 2 + ["edit_docx_review"]


def test_the_models_own_write_is_not_taken_for_the_persons(tmp_path):
    (tmp_path / "a.docx").write_bytes(b"one")
    guard, ran = _guard(tmp_path)
    _run(guard, _call("read_docx_review", "a.docx"))

    def writing(request: Any) -> ToolMessage:
        (tmp_path / "a.docx").write_bytes(b"two")
        return ToolMessage(content="ok", tool_call_id="c1", name="edit_docx_review")

    guard.wrap_tool_call(_call("edit_docx_review", "a.docx"), writing)
    assert _run(guard, _call("edit_docx_review", "a.docx")).content == "ok"
    assert ran[-1] == "edit_docx_review"


def test_a_file_never_read_and_a_file_of_another_kind_are_not_guarded(tmp_path):
    (tmp_path / "a.docx").write_bytes(b"one")
    (tmp_path / "n.txt").write_bytes(b"one")
    guard, ran = _guard(tmp_path)
    assert _run(guard, _call("edit_docx_review", "a.docx")).content == "ok"
    (tmp_path / "a.docx").write_bytes(b"two")
    guard._seen.clear()
    assert _run(guard, _call("edit_docx_review", "a.docx")).content == "ok"
    _run(guard, _call("edit_docx_review", "n.txt"))
    (tmp_path / "n.txt").write_bytes(b"two")
    assert _run(guard, _call("edit_docx_review", "n.txt")).content == "ok"


def test_the_async_path_refuses_too(tmp_path):
    (tmp_path / "a.docx").write_bytes(b"one")
    guard, _ = _guard(tmp_path)
    _run(guard, _call("read_docx_review", "a.docx"))
    (tmp_path / "a.docx").write_bytes(b"two")

    async def handler(request: Any) -> ToolMessage:
        raise AssertionError("must not run")

    refused = asyncio.run(guard.awrap_tool_call(_call("edit_docx_review", "a.docx"), handler))
    assert refused.status == "error"
