"""How each turn went, kept on this machine: one JSON line per turn with its model calls,
tokens, tools and outcome (decision 0045). It holds none of the conversation's words: no
message text, no tool arguments and no tool results, only the start of a tool's error text."""

from __future__ import annotations

import contextlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .audit import redact_secrets

Outcome = Literal["completed", "stopped", "error"]

# An error's first lines name what went wrong; the rest is usually the content it choked on.
_ERROR_CHARS = 300
# A turn that fails the same way fifty times says nothing more the fiftieth time.
_ERRORS_KEPT = 20
# About ten thousand turns. The file before it is kept, so a reader always has a recent run
# of turns, and nothing grows without a limit on a disk nobody looks at.
_MAX_BYTES = 5_000_000


@dataclass
class TurnTrace:
    started: str
    thread_id: str
    model: str
    effort: str
    mode: str
    # A sub-agent's or a background task's report runs as a turn nobody typed.
    notice: bool
    seconds: float
    outcome: Outcome
    # The exception's type for a turn that ended on one; its text can quote the conversation.
    error: str | None
    model_calls: int
    input_tokens: int
    cached_tokens: int
    output_tokens: int
    # Tool name to {"calls": n, "errors": m}.
    tools: dict[str, dict[str, int]]
    tool_errors: list[dict[str, str]] = field(default_factory=list)


class TraceLog:
    """One append-only file for every conversation, as `AuditLog` is: a turn's line is joined
    to its approval decisions by thread and time."""

    def __init__(self, state_dir: str | Path) -> None:
        self.path = Path(state_dir) / "turns.jsonl"

    def append(self, entry: TurnTrace) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_file() and self.path.stat().st_size > _MAX_BYTES:
            self.path.replace(self.path.with_suffix(".1.jsonl"))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def read_all(self) -> list[TurnTrace]:
        """Every turn in the current file, oldest first. A line that does not parse (a cut-off
        write, a file edited by hand) is skipped: one bad line must not hide the rest."""
        if not self.path.is_file():
            return []
        entries = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    entries.append(TurnTrace(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        return entries


class TurnRecorder:
    """Counts one turn as it runs and writes its line when it ends. Writing never fails the
    turn: a full disk or a locked file loses the line, not the reply."""

    def __init__(
        self,
        log: TraceLog,
        *,
        thread_id: str,
        model: str,
        effort: str,
        mode: str,
        notice: bool = False,
    ) -> None:
        self._log = log
        self._started = datetime.now(UTC).isoformat()
        self._clock = time.monotonic()
        self._thread_id = thread_id
        self._model = model
        self._effort = effort
        self._mode = mode
        self._notice = notice
        self._model_calls = 0
        self._input = self._cached = self._output = 0
        self._tools: dict[str, dict[str, int]] = {}
        self._tool_errors: list[dict[str, str]] = []
        self._finished = False

    def model_call(self, usage: Any) -> None:
        """One model response. `usage` is its `usage_metadata`, or None from a provider that
        reports none: the call still counts."""
        self._model_calls += 1
        if not usage:
            return
        self._input += int(usage.get("input_tokens") or 0)
        self._output += int(usage.get("output_tokens") or 0)
        self._cached += int((usage.get("input_token_details") or {}).get("cache_read") or 0)

    def tool(self, name: str, *, is_error: bool, result: Any = None) -> None:
        count = self._tools.setdefault(name, {"calls": 0, "errors": 0})
        count["calls"] += 1
        if not is_error:
            return
        count["errors"] += 1
        if len(self._tool_errors) < _ERRORS_KEPT:
            text = result if isinstance(result, str) else json.dumps(result, default=str)
            self._tool_errors.append(
                {"tool": name, "text": str(redact_secrets(text[:_ERROR_CHARS]))}
            )

    def finish(self, outcome: Outcome, error: BaseException | None = None) -> None:
        if self._finished:
            return
        self._finished = True
        if not self._model_calls and not self._tools and error is None:
            # A command such as /plan, or a stop before anything ran: nothing to learn from.
            return
        entry = TurnTrace(
            started=self._started,
            thread_id=self._thread_id,
            model=self._model,
            effort=self._effort,
            mode=self._mode,
            notice=self._notice,
            seconds=round(time.monotonic() - self._clock, 2),
            outcome=outcome,
            error=type(error).__name__ if error is not None else None,
            model_calls=self._model_calls,
            input_tokens=self._input,
            cached_tokens=self._cached,
            output_tokens=self._output,
            tools=self._tools,
            tool_errors=self._tool_errors,
        )
        with contextlib.suppress(OSError):
            self._log.append(entry)


def tool_failure_rates(entries: list[TurnTrace]) -> list[tuple[str, int, int]]:
    """(tool, calls, errors) over `entries`, the tool that failed most often first."""
    totals: dict[str, list[int]] = {}
    for entry in entries:
        for name, count in entry.tools.items():
            total = totals.setdefault(name, [0, 0])
            total[0] += count.get("calls", 0)
            total[1] += count.get("errors", 0)
    rows = [(name, calls, errors) for name, (calls, errors) in totals.items()]
    return sorted(rows, key=lambda row: (-row[2], -row[1], row[0]))
