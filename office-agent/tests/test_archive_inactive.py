"""Conversations idle past the setting are archived when the sidebar lists them."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from coscribe.conversation import ThreadMetaStore
from coscribe.web.routes.threads import _archive_inactive


def _summary(thread_id: str, days_idle: float, status: str = "idle") -> dict[str, Any]:
    ts = datetime.now(UTC) - timedelta(days=days_idle)
    return {
        "thread_id": thread_id,
        "updated_at": ts.isoformat(),
        "archived": False,
        "status": status,
    }


def _state(tmp_path: Path, days: int | None, open_threads: tuple[str, ...] = ()) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(archive_inactive_days=days),
        meta_store=ThreadMetaStore(tmp_path),
        sessions={t: object() for t in open_threads},
    )


def test_only_a_conversation_idle_past_the_limit_is_archived(tmp_path: Path) -> None:
    state = _state(tmp_path, 7)
    old, recent = _summary("old", 10), _summary("recent", 2)

    _archive_inactive(state, [old, recent])

    assert old["archived"] is True and state.meta_store.get("old")["archived"] is True
    assert recent["archived"] is False and state.meta_store.get("recent")["archived"] is False


def test_nothing_is_archived_when_the_setting_is_never(tmp_path: Path) -> None:
    old = _summary("old", 400)

    _archive_inactive(_state(tmp_path, None), [old])

    assert old["archived"] is False


def test_a_running_waiting_or_open_conversation_is_left_alone(tmp_path: Path) -> None:
    state = _state(tmp_path, 7, open_threads=("open",))
    summaries = [
        _summary("working", 30, "working"),
        _summary("waiting", 30, "needs_input"),
        _summary("open", 30),
    ]

    _archive_inactive(state, summaries)

    assert not any(s["archived"] for s in summaries)


def test_a_conversation_taken_out_of_the_archive_by_hand_stays_out(tmp_path: Path) -> None:
    state = _state(tmp_path, 7)
    state.meta_store.update("back", archived=False, kept=True)
    back = _summary("back", 30)

    _archive_inactive(state, [back])

    assert back["archived"] is False
