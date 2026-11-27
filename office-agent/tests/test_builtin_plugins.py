"""A built-in plugin brings tools of the app (decision 0058): switched off, its skills are not
offered and its tools are neither found nor run, while the tools bound to the model stay the
same."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from coscribe.config import Settings
from coscribe.conversation import ChatSessionLG, agent_assembly
from coscribe.conversation import session as conversation_session
from coscribe.conversation.capability_guard import TurnedOff, held_plugin_tools, plugin_refusal
from coscribe.runtime import empty_hooks_config, get_tool_metadata

from .web.helpers import FakeToolCallingChatModel

PAGES_TOOL = "build_pptx_from_pages"


class _ContextWindow:
    def get_context_window(self, model: str) -> int:
        return 128000


def _session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    enabled: set[str],
    custom_providers: dict[str, dict[str, str]] | None = None,
    model: str = "fake:model",
) -> tuple[ChatSessionLG, list[list[str]]]:
    """A conversation, and the tool names each agent it builds is given."""
    monkeypatch.setattr(
        conversation_session,
        "resolve_chat_model",
        lambda name, custom_providers=None: FakeToolCallingChatModel(responses=[]),
    )
    built: list[list[str]] = []
    real = agent_assembly.build_langgraph_agent

    def capture(model: Any, tools: list[Any], *args: Any, **kwargs: Any) -> Any:
        built.append([agent_assembly.tool_name(t) for t in tools])
        return real(model, tools, *args, **kwargs)

    monkeypatch.setattr(agent_assembly, "build_langgraph_agent", capture)
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        default_model=model,
        workspace_root=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        skills_dir=tmp_path / "skills",
        memory_path=tmp_path / "MEMORY.md",
        auto_title_threads=False,
        prompt_suggestions=False,
        folder_briefs=False,
        save_offers=False,
    )
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    session = ChatSessionLG(
        thread_id="t1",
        settings=settings,
        context_window_client=_ContextWindow(),
        custom_providers=custom_providers or {},
        extra_tools=[],
        checkpointer=InMemorySaver(),
        hooks_config=empty_hooks_config(),
        enabled_skill_names=enabled,
        workspace_root=tmp_path / "workspace",
    )
    return session, built


def test_pptx_pages_off_holds_its_tool_and_nothing_else() -> None:
    assert held_plugin_tools({"Word Documents"}) == {PAGES_TOOL: "pptx-pages"}
    assert held_plugin_tools({"PPTX Pages"}) == {}
    assert "Settings › Plugins" in (plugin_refusal(PAGES_TOOL, set()) or "")
    assert plugin_refusal("write_pptx", set()) is None


def test_off_its_tool_is_not_found_and_refuses_with_the_same_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on, built_on = _session(tmp_path / "on", monkeypatch, {"PPTX Pages"})
    assert PAGES_TOOL in built_on[-1]
    off, built_off = _session(tmp_path / "off", monkeypatch, set())

    assert PAGES_TOOL not in built_off[-1]
    [held] = [t for t in off._base_tools if t.__name__ == PAGES_TOOL]
    [plain] = [t for t in on._base_tools if t.__name__ == PAGES_TOOL]
    assert held.__doc__ == plain.__doc__
    assert get_tool_metadata(held) == get_tool_metadata(plain)
    with pytest.raises(TurnedOff, match="pptx-pages plugin is turned off"):
        held(pages_dir="deck-pages", path="deck.pptx")


def test_where_every_tool_is_bound_the_list_keeps_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deepseek = {"ds": {"base_url": "https://api.deepseek.com/v1"}}
    _, built = _session(tmp_path, monkeypatch, set(), deepseek, model="ds:deepseek-flash")

    assert PAGES_TOOL in built[-1]
