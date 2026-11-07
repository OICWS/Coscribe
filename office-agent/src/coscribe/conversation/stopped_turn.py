"""What a turn the user stopped leaves behind. The reply it had written so far stays in the
history and on the page instead of being replaced by a bare marker, and the next turn starts
knowing it was stopped, which calls were cut off and what still runs in the background (a stop
leaves background work going)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from langgraph.graph import END

from ..runtime_lg import stopped_turn_messages
from ..tools import BackgroundTaskStore, SubAgentTaskStore
from .history import close_orphaned_tool_calls


class StoppedTurnHost(Protocol):
    thread_id: str
    settings: Any
    lg_agent: Any
    config: dict[str, Any]
    _stop_requested: bool


def still_running(state_dir: str | Path, thread_id: str) -> list[str]:
    """The background scripts, commands and sub-agents of the conversation that still run."""
    scripts = BackgroundTaskStore(state_dir).list_for_thread(thread_id)
    agents = SubAgentTaskStore(state_dir).list_for_thread(thread_id)
    return [f'"{t.description}"' for t in scripts if t.status == "running"] + [
        f'sub-agent "{t.description}"' for t in agents if t.background and t.status == "running"
    ]


async def keep_stopped_turn(host: StoppedTurnHost, text: str, *, keep: bool = True) -> str:
    """Writes what the stopped turn said and the note for the next one into the history, and
    returns what the page shows for the turn. A turn cancelled without a stop (the socket
    dropped) keeps nothing, since a reconnect resumes it."""
    if not host._stop_requested:
        return "[stopped]"
    running = still_running(host.settings.state_dir, host.thread_id)
    shown = f"{text.strip()}\n\n[stopped]" if text.strip() else "[stopped]"
    if running:
        shown += (
            f"\n\n({len(running)} background task(s) still running; "
            "stop them in the Background tasks panel.)"
        )
    # A conversation being deleted must not be written back.
    if not keep:
        return shown
    agent, config = host.lg_agent, host.config
    await close_orphaned_tool_calls(agent, config)
    state = await agent.aget_state(config)
    if not state.values or any(task.interrupts for task in state.tasks):
        return shown
    added = stopped_turn_messages(list(state.values.get("messages", [])), text, running)
    await agent.aupdate_state(config, {"messages": added}, as_node="tools")
    await agent.aupdate_state(config, None, as_node=END)
    return shown
