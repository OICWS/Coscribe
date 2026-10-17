"""What the model is sent that providers cache, written down so a change shows.

Decision 0001: the tool list bound to the model and the system prompt are the same for
every conversation, and providers cache them by prefix. `tests/test_prompt_cache.py` pins
that two conversations get the same ones. This pins what they are: a checked-in snapshot
(`tests/tool_schemas.txt`) lists the system prompt's size and hash, each tool bound to the
model (its parameters and the hash of its description), and every registered tool with its
risk tier. Changing a tool's name, parameters or description, or the system prompt, edits
the snapshot in the same pull request, so a reviewer sees which tools changed and how big
the cached prefix became. `UPDATE_TOOL_SCHEMAS=1 pytest tests/test_tool_schema_snapshot.py`
rewrites it; read the diff before committing it.

The token counts are characters divided by four: a measure of change, not of cost.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from coscribe.coordinator import CORE_TOOL_NAMES
from coscribe.runtime import get_tool_metadata
from coscribe.runtime_lg.agent import tool_name

from .test_prompt_cache import _RecordingModel, _session, _Socket

SNAPSHOT = Path(__file__).with_name("tool_schemas.txt")


class _BindingModel(_RecordingModel):
    """Keeps the tools the agent binds, as a provider would receive them."""

    bound: list[Any] = []

    def bind_tools(self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any) -> Any:
        self.bound = list(tools)
        return self


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


def _tokens(chars: int) -> int:
    return chars // 4


def _parameters(function: dict[str, Any]) -> str:
    schema = function.get("parameters", {})
    required = set(schema.get("required", []))
    parts = []
    for name, spec in sorted(schema.get("properties", {}).items()):
        kind = spec.get("type") or "|".join(
            str(option.get("type", "?")) for option in spec.get("anyOf", [])
        )
        parts.append(f"{name}{'' if name in required else '?'}:{kind or '?'}")
    return ", ".join(parts)


async def _describe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, thread: str = "snapshot"
) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    model = _BindingModel(responses=[AIMessage(content="ok")])
    session = _session(tmp_path, monkeypatch, model, thread, tmp_path / "folder")
    await session.handle_user_message("hello", _Socket())  # type: ignore[arg-type]
    # The one install-specific part of the prompt: where new skills are written. It is the
    # same for every conversation of an install, so the cache is not affected, but it is not
    # the same for two installs, so it is replaced before the prompt is measured.
    system = str(model.received[0][0].content).replace(
        str(session.settings.skills_dir), "<skills dir>"
    )
    assert str(tmp_path) not in system, "a path from this conversation is in the system prompt"

    bound = sorted(
        (convert_to_openai_tool(tool)["function"] for tool in model.bound),
        key=lambda function: function["name"],
    )
    bound_chars = sum(len(f.get("description", "")) + len(str(f.get("parameters"))) for f in bound)
    registered = sorted(session._build_lg_tools(model), key=tool_name)  # noqa: SLF001
    registered_chars = sum(
        len(str(convert_to_openai_tool(tool)["function"])) for tool in registered
    )

    lines = [
        "# The model is sent: the system prompt, then the tools bound to it (decision 0001).",
        "# A change here is a change to what providers cache. UPDATE_TOOL_SCHEMAS=1 rewrites it.",
        "",
        f"system prompt: {len(system)} chars, ~{_tokens(len(system))} tokens, "
        f"sha256 {_hash(system)}",
        "",
        f"bound to the model: {len(bound)} tools, ~{_tokens(bound_chars)} tokens",
    ]
    for function in bound:
        description = function.get("description", "")
        lines.append(
            f"  {function['name']} ({_parameters(function)}) "
            f"desc {len(description)} chars sha256 {_hash(description)}"
        )
    lines += [
        "",
        f"registered: {len(registered)} tools, ~{_tokens(registered_chars)} tokens "
        "(the ones not bound are found through search_tools)",
    ]
    for tool in registered:
        name = tool_name(tool)
        metadata = get_tool_metadata(tool)
        where = "core" if name in CORE_TOOL_NAMES else "deferred"
        description = convert_to_openai_tool(tool)["function"].get("description", "")
        lines.append(
            f"  {name} | {metadata.risk_category} | {metadata.category or '-'} | {where} "
            f"| sha256 {_hash(description)}"
        )
    return "\n".join(lines) + "\n"


@pytest.mark.skipif(
    sys.version_info >= (3, 13),
    reason="Python 3.13 strips docstring indentation, so every tool description hashes differently "
    "from the snapshot; CI runs 3.11, which is the check",
)
async def test_the_system_prompt_and_tool_schemas_match_the_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = await _describe(tmp_path, monkeypatch)

    if os.environ.get("UPDATE_TOOL_SCHEMAS"):
        SNAPSHOT.write_text(current, encoding="utf-8", newline="\n")
    expected = SNAPSHOT.read_text(encoding="utf-8")
    assert current == expected, (
        "What the model is sent changed. If that is intended, run "
        "`UPDATE_TOOL_SCHEMAS=1 pytest tests/test_tool_schema_snapshot.py`, read the diff of "
        "tests/tool_schemas.txt and commit it (decision 0001)."
    )


async def test_the_snapshot_does_not_depend_on_the_folder_or_the_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same description from two conversations in other folders: nothing in it may come
    from the conversation (a path, a thread id, a secret's name)."""
    one = await _describe(tmp_path / "a", monkeypatch, "first-conversation")
    two = await _describe(tmp_path / "bb", monkeypatch, "2")

    assert one == two
