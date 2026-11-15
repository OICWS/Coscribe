"""Task tracking: a lightweight, per-thread todo list the Coordinator can use
to plan and track progress on multi-step requests.

This is Coordinator-native behavior (see ARCHITECTURE.md's "One coordinator",
modeled on claude-code's TaskCreate/TaskUpdate tools), not something borrowed
via MCP/Skill, so it ships as a built-in tool family alongside the file tools.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ...runtime import tool_metadata
from .._file_locks import file_lock, read_text_with_retry, replace_with_retry

VALID_STATUSES = ("pending", "in_progress", "completed")


class TaskToolkit:
    """A todo list scoped to one conversation thread.

    Persisted to its own JSON file, thread-id-derived like the checkpointer's
    own storage, but kept as a separate file: tasks aren't part of the
    message history the checkpointer manages, and are read/written
    synchronously on every mutation rather than only at the end of a run.
    """

    def __init__(self, thread_id: str, state_dir: str | Path) -> None:
        self._path = Path(state_dir) / f"{quote(thread_id, safe='')}.tasks.json"

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return list(json.loads(read_text_with_retry(self._path)))

    def _change(self, edit: Callable[[list[dict[str, Any]]], Any]) -> Any:
        """Read the file, apply `edit` to its list, write it back, all under the file's lock.

        Another TaskToolkit on the same thread (the person's edits to a plan under review are
        written by the approval code, not the tool's own instance) may have written since this
        one last looked, so a change starts from the file, never from a list kept in memory.
        task_create is READ and ungated, so several calls of one answer run in threads at once;
        the per-file lock, shared by every instance, keeps them from computing the same next id
        or racing on the tmp file's name."""
        with file_lock(self._path.resolve()):
            tasks = self._load()
            result = edit(tasks)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._path.with_suffix(".tmp")
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(tasks, handle, ensure_ascii=False, indent=2)
            replace_with_retry(tmp_path, self._path)
        return result

    @staticmethod
    def _next_id(tasks: list[dict[str, Any]]) -> str:
        return str(max((int(task["id"]) for task in tasks), default=0) + 1)

    def create(self, content: str) -> dict[str, Any]:
        def add(tasks: list[dict[str, Any]]) -> dict[str, Any]:
            task = {"id": self._next_id(tasks), "content": content, "status": "pending"}
            tasks.append(task)
            return task

        return dict(self._change(add))

    def update(self, task_id: str, status: str) -> dict[str, Any]:
        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}, got {status!r}")

        def set_status(tasks: list[dict[str, Any]]) -> dict[str, Any]:
            for task in tasks:
                if task["id"] == task_id:
                    task["status"] = status
                    return dict(task)
            raise KeyError(f"No task with id {task_id!r}")

        return dict(self._change(set_status))

    def replace(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """The list as the person left it when reviewing a plan, in their order: an item with
        the id of a task keeps that task's status, one without (or with an id no task has) is
        a new pending task, and a task the list leaves out is gone. A new item's id is past every
        id of the old list, so a task_update aimed at a removed task fails instead of landing on
        an item the person added."""

        def rebuild(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
            by_id = {task["id"]: task for task in tasks}
            next_id = int(self._next_id(tasks))
            kept: list[dict[str, Any]] = []
            for item in items:
                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                old = by_id.pop(str(item.get("id", "")), None)
                if old is not None:
                    kept.append({**old, "content": content})
                else:
                    kept.append({"id": str(next_id), "content": content, "status": "pending"})
                    next_id += 1
            tasks[:] = kept
            return [dict(task) for task in kept]

        return list(self._change(rebuild))

    def list_tasks(self) -> list[dict[str, Any]]:
        return self._load()

    def open_tasks_note(self) -> str:
        """The unfinished tasks, for the message after a compaction's summary: the summary is
        written from the transcript, which can miss a task created before the part it saw."""
        lines = [
            f"- [{task['status']}] {task['id']}: {task['content']}"
            for task in self.list_tasks()
            if task["status"] != "completed"
        ]
        if not lines:
            return ""
        return "Open tasks in your plan (task_update them as you go):\n" + "\n".join(lines)


def build_task_tools(thread_id: str, state_dir: str | Path) -> list[Callable[..., Any]]:
    """Return the task-tracking tool callables, bound to one conversation thread."""
    toolkit = TaskToolkit(thread_id, state_dir)

    def task_create(content: str) -> dict[str, Any]:
        """Add a new task to the plan for this conversation.

        Args:
            content: short imperative description of the task, e.g. "Read config.py"
        """
        return toolkit.create(content)

    def task_update(task_id: str, status: str) -> dict[str, Any]:
        """Update a task's status as you make progress. Mark each task completed
        as soon as it's done; don't batch updates.

        Args:
            task_id: id of the task to update, as returned by task_create/task_list
            status: one of "pending", "in_progress", "completed"
        """
        return toolkit.update(task_id, status)

    def task_list() -> list[dict[str, Any]]:
        """List all tasks in the current plan, in creation order."""
        return toolkit.list_tasks()

    return [
        # READ, not WRITE_LOCAL, despite writing a state file -- deliberately
        # kept ungated (preserving current behavior): task tracking is
        # thread-scoped, disposable bookkeeping the model uses constantly as
        # part of ordinary multi-step work (visible throughout this
        # project's own live-verification sessions as routine
        # task_create/task_update calls), unlike a tool that persists
        # something durable -- gating this the same way would make approval-fatigue the
        # normal state of using the tool at all, for something with no
        # real externally-visible consequence.
        tool_metadata(task_create, risk_category="READ", category="tasks"),
        tool_metadata(task_update, risk_category="READ", category="tasks"),
        tool_metadata(task_list, risk_category="READ", category="tasks"),
    ]
