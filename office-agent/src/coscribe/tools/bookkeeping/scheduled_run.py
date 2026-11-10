"""One run of a scheduled task: what started it, how it went and what it left (the store
that keeps runs is `scheduled_tasks.py`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScheduledRun:
    """One execution of a trigger, in its own fresh conversation -- never
    the thread the task was created from, and never a previous run's, so
    history doesn't pile up run after run (continuity comes from the
    task's notes instead)."""

    run_id: str
    thread_id: str
    started_at: str
    # "manual" (Run now) | "scheduled" | "file" (a new file in its folder) | "connector" (a new
    # item in a connector's answer, decision 0039)
    source: str
    status: str = "running"  # one of RUN_STATUSES
    finished_at: str | None = None
    error: str | None = None
    # A workflow run's per-step records (workflows/engine.py's StepRecord),
    # in the order the steps first ran, and the inputs it was given.
    steps: list[dict[str, Any]] = field(default_factory=list)
    inputs: dict[str, Any] | None = None
    # Where a browser workflow run failed: a page_screenshot file name and
    # the page's text, for the person and the assistant looking into it.
    screenshot: str | None = None
    page: str | None = None
    # What a completed run wrote ({"path", "size", "rows"?, "columns"?}),
    # and the conversation looking into a failed one.
    files: list[dict[str, Any]] = field(default_factory=list)
    investigation: str | None = None
    # The sites a workflow run opened, as hosts.
    sites: list[str] = field(default_factory=list)
    queued: bool = False  # waiting for the browser, which one run uses at a time
    # A run a check ended with nothing to do (decision 0034): how many such runs in a row this
    # record stands for, since only the latest of a row is kept; 0 for any other run.
    quiet: int = 0
    # The versions of its task it ran (decision 0035), and per run-task step ("<step>" or
    # "<step>/<its step>"): {"task", "name", "version", "workflow"} of the task it ran.
    versions: list[int] = field(default_factory=list)
    called: dict[str, Any] = field(default_factory=dict)
    # What started a "connector" run: {"connector", "tool", "key", "item"}.
    event: dict[str, Any] | None = None
    # The tokens a person let this run's models use, past its own cap (decision 0043).
    token_cap: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "thread_id": self.thread_id,
            "started_at": self.started_at,
            "source": self.source,
            "status": self.status,
            "finished_at": self.finished_at,
            "error": self.error,
            "steps": self.steps,
            "inputs": self.inputs,
            "screenshot": self.screenshot,
            "page": self.page,
            "files": self.files,
            "investigation": self.investigation,
            "sites": self.sites,
            "queued": self.queued,
            "quiet": self.quiet,
            "versions": self.versions,
            "called": self.called,
            "event": self.event,
            "token_cap": self.token_cap,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledRun:
        return cls(
            run_id=data["run_id"],
            thread_id=data["thread_id"],
            started_at=data["started_at"],
            source=data.get("source", "scheduled"),
            status=data.get("status", "completed"),
            finished_at=data.get("finished_at"),
            error=data.get("error"),
            steps=data.get("steps") or [],
            inputs=data.get("inputs"),
            screenshot=data.get("screenshot"),
            page=data.get("page"),
            files=data.get("files") or [],
            investigation=data.get("investigation"),
            sites=list(data.get("sites") or []),
            queued=bool(data.get("queued", False)),
            quiet=int(data.get("quiet") or 0),
            versions=[int(v) for v in data.get("versions") or []],
            called=dict(data.get("called") or {}),
            event=data.get("event"),
            token_cap=data.get("token_cap"),
        )


def fold_quiet(runs: list[ScheduledRun]) -> tuple[list[ScheduledRun], list[ScheduledRun]]:
    """Keep only the latest of each row of quiet runs, counting the ones it stands for: a task
    that checks every few minutes would otherwise bury its real runs."""
    kept: list[ScheduledRun] = []
    dropped: list[ScheduledRun] = []
    for run in runs:
        if kept and kept[-1].quiet and run.quiet and run.status == kept[-1].status == "completed":
            run.quiet += kept[-1].quiet
            dropped.append(kept.pop())
        kept.append(run)
    return kept, dropped
