"""A task's model answers kept as a tape, and the task run again from the tape with no model.

    python -m evals.agentic.run --tasks 08 --out evals/runs/tape --record evals/agentic/tapes

A real run writes one tape per task that completed without the nudge: every answer a model
gave, in order, what each script it ran printed and how it ended, and the names of the tools each
turn called. `replay_task` runs the task again
with those answers in place of the model: the agent loop, its middleware, the approvals and
every tool run for real, in a fresh folder, except that a script's interpreter is not started:
its recorded output stands in, so a replay needs no Python environment, Node or network. It is
the part of the evaluation the pull request
checks can afford (`tests/test_evals_agentic_replay.py`).

What a replay catches is a change in what coscribe does with the same answers: a turn-end check
that fires differently, a tool that now fails, a compaction that drops what a later turn needs.
What it cannot say is whether a model would still answer this way after a prompt changed; that
takes the real run. A tape that no longer fits (the run asks for an answer the tape lacks, or
ends with answers left) fails with a message saying to record it again.
"""

from __future__ import annotations

import base64
import contextlib
import contextvars
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

TAPES = Path(__file__).resolve().parent / "tapes"
# A path the model wrote into a call belongs to the folder of the run that recorded it.
_WORKSPACE = "{{WORKSPACE}}"
_ROOT = "{{ROOT}}"
# The agent and its sub-agents are bound to the whole tool list; a side job (a verdict, a
# title, a folder's brief) to none, or to the one schema its answer is read from.
_AGENT_TOOLS = 5


class TapeMismatch(Exception):
    """The run and the tape disagree about which answers are needed."""


def _kind(tool_count: int) -> str:
    return "agent" if tool_count >= _AGENT_TOOLS else "side"


@dataclass
class Tape:
    """The answers of one task's run, each with the kind of call it answered. Answers of one
    kind are given in the order they were recorded; the two kinds overlap in time (a side job
    runs beside the turn), so they are not held to one order between them."""

    task: str
    model: str = ""
    effort: str = ""
    entries: list[dict[str, Any]] = field(default_factory=list)
    calls: list[list[str]] = field(default_factory=list)
    # The model's context window as the recording run read it: compaction starts at a share of it.
    window: int = 0
    # What the provider's messages call it. The compaction trusts a message's token count only
    # when the message and the model name the same provider.
    provider: str = ""
    # What each Python or Node script printed and how it ended, in the order they ran.
    scripts: list[dict[str, Any]] = field(default_factory=list)
    used: set[int] = field(default_factory=set)
    # Answers the run asked for and the tape could not give. A sub-agent or a reviewer turns the
    # error into text of its own, so only this count says the replay went off the tape.
    missed: int = 0
    scripts_used: int = 0

    def add(self, kind: str, message: Any) -> None:
        content = message.content
        if not isinstance(content, str):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        calls = [
            {"name": call["name"], "args": call["args"], "id": call["id"]}
            for call in getattr(message, "tool_calls", None) or []
        ]
        usage = getattr(message, "usage_metadata", None)
        self.provider = message.response_metadata.get("model_provider") or self.provider
        self.entries.append(
            {"kind": kind, "content": content, "tool_calls": calls, "usage": usage}
        )

    def next(self, kind: str) -> AIMessage:
        for index, entry in enumerate(self.entries):
            if index not in self.used and entry["kind"] == kind:
                self.used.add(index)
                return AIMessage(
                    content=entry["content"],
                    tool_calls=entry["tool_calls"],
                    usage_metadata=entry.get("usage"),
                    response_metadata={"model_provider": self.provider},
                )
        self.missed += 1
        raise TapeMismatch(
            f"{self.task}: the run asked for one more {kind} answer than the tape holds. "
            "coscribe now does something else with the same answers; if that is intended, "
            "record the tape again (see evals/agentic/replay.py)."
        )

    def add_script(self, ran: Any, files: dict[str, str]) -> None:
        self.scripts.append(
            {
                "returncode": ran.returncode,
                "stdout": ran.stdout,
                "stderr": ran.stderr,
                "timed_out": ran.timed_out,
                # A script let go to the background ends outside the turn: no replay can hold it.
                "detached": ran.detached is not None,
                # What it wrote in the workspace, which a later step may read (base64).
                "files": files,
            }
        )

    def next_script(self, cwd: Path) -> Any:
        from coscribe.tools.exec.running import Ran

        if self.scripts_used >= len(self.scripts):
            self.missed += 1
            raise TapeMismatch(
                f"{self.task}: the run started one more script than the tape holds. Record the "
                "tape again (see evals/agentic/replay.py)."
            )
        recorded = self.scripts[self.scripts_used]
        self.scripts_used += 1
        if recorded["detached"]:
            self.missed += 1
            raise TapeMismatch(f"{self.task}: a script went to the background; record again.")
        for name, data in recorded.get("files", {}).items():
            target = cwd / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(data))
        return Ran(
            recorded["returncode"], recorded["stdout"], recorded["stderr"], recorded["timed_out"]
        )

    def left(self) -> int:
        return len(self.entries) - len(self.used) + len(self.scripts) - self.scripts_used

    def save(self, path: Path, workspace: Path, root: Path) -> None:
        body = {
            "task": self.task,
            "model": self.model,
            "effort": self.effort,
            "window": self.window,
            "provider": self.provider,
            "calls": self.calls,
            "scripts": self.scripts,
        }
        text = json.dumps({**body, "entries": self.entries}, ensure_ascii=False, indent=1)
        for real, mark in ((workspace, _WORKSPACE), (root, _ROOT)):
            # Both spellings: as the path is, and as JSON writes a Windows path's backslashes.
            text = text.replace(json.dumps(str(real))[1:-1], mark).replace(str(real), mark)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path, workspace: Path, root: Path) -> Tape:
        text = path.read_text(encoding="utf-8")
        for real, mark in ((workspace, _WORKSPACE), (root, _ROOT)):
            text = text.replace(mark, json.dumps(str(real))[1:-1])
        data = json.loads(text)
        return cls(
            data["task"],
            data["model"],
            data["effort"],
            data["entries"],
            data["calls"],
            data["window"],
            data["provider"],
            data.get("scripts", []),
        )


_CURRENT: contextvars.ContextVar[Tape | None] = contextvars.ContextVar("eval_tape", default=None)


# The tapes of the tasks running now. A call made in a fresh context (review_work runs its
# reviewer in one, so that its tokens do not stream into the chat) cannot see its task's tape.
_ACTIVE: list[Tape] = []


def use(tape: Tape) -> None:
    """Make `tape` the one the task running in this context records to or answers from."""
    _CURRENT.set(tape)
    _ACTIVE.append(tape)


def release(tape: Tape) -> None:
    """The task of `tape` has ended."""
    if tape in _ACTIVE:
        _ACTIVE.remove(tape)


def _current() -> Tape | None:
    tape = _CURRENT.get()
    if tape is not None or not _ACTIVE:
        return tape
    if len(_ACTIVE) > 1:
        raise RuntimeError(
            "a model call outside its task's context while several tasks run: record with --jobs 1"
        )
    return _ACTIVE[0]


def _tape() -> Tape:
    tape = _current()
    if tape is None:
        for running in _ACTIVE:
            running.missed += 1
        raise RuntimeError("no tape is set for this task (replay.use)")
    return tape


_FILES_KEPT = 5_000_000


def _workspace_files(root: Path) -> dict[str, tuple[int, int]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in root.rglob("*")
        if path.is_file()
    }


def _written(root: Path, before: dict[str, tuple[int, int]]) -> dict[str, str]:
    """The files under `root` a script created or changed, as base64."""
    changed = {
        name: base64.b64encode((root / name).read_bytes()).decode("ascii")
        for name, stamp in _workspace_files(root).items()
        if before.get(name) != stamp
    }
    if sum(len(data) for data in changed.values()) > _FILES_KEPT:
        raise RuntimeError("a script wrote more than a tape keeps; this task cannot be taped")
    return changed


def _cwd(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Path:
    return Path(args[1] if len(args) > 1 else kwargs["cwd"])


class _Record(BaseCallbackHandler):
    def __init__(self) -> None:
        self._kinds: dict[Any, str] = {}

    def on_chat_model_start(
        self, serialized: Any, messages: Any, *, run_id: Any, **kwargs: Any
    ) -> None:
        tools = (kwargs.get("invocation_params") or {}).get("tools") or []
        self._kinds[run_id] = _kind(len(tools))

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        kind = self._kinds.pop(run_id, None)
        tape = _current()
        if kind is None or tape is None:
            return
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if message is not None:
                    tape.add(kind, message)


class TapeModel(BaseChatModel):
    """A chat model that answers from the current task's tape."""

    tool_count: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self.model_copy(update={"tool_count": len(list(tools))})

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(
            generations=[ChatGeneration(message=_tape().next(_kind(self.tool_count)))]
        )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Any:
        # One piece per answer, as a provider's last piece would be: the turn's stream only
        # forwards pieces, never a whole message.
        message = _tape().next(_kind(self.tool_count))
        yield ChatGenerationChunk(
            message=AIMessageChunk(
                content=message.content,
                tool_calls=message.tool_calls,
                usage_metadata=message.usage_metadata,
                response_metadata=message.response_metadata,
            )
        )

    def _get_ls_params(self, stop: list[str] | None = None, **kwargs: Any) -> Any:
        tape = _current()
        return {**super()._get_ls_params(stop, **kwargs), "ls_provider": tape and tape.provider}

    @property
    def _llm_type(self) -> str:
        return "eval-tape"


@contextlib.contextmanager
def _models(build: Any) -> Iterator[None]:
    """Every place a conversation builds a chat model builds it through `build(original)`."""
    from coscribe.conversation import agent_assembly, session, subagents

    modules = (session, agent_assembly, subagents)
    originals = [module.resolve_chat_model for module in modules]
    for module, original in zip(modules, originals, strict=True):
        module.resolve_chat_model = build(original)  # type: ignore[attr-defined]
    try:
        yield
    finally:
        for module, original in zip(modules, originals, strict=True):
            module.resolve_chat_model = original  # type: ignore[attr-defined]


@contextlib.contextmanager
def _scripts(run: Any, *, prepared: bool) -> Iterator[None]:
    """Both script tools start their interpreter through `run(original_run_to_end)`. Unless
    `prepared`, the environments and isolation a real interpreter needs are not set up."""
    from coscribe.tools.exec import node_scripts, scripts

    modules = (scripts, node_scripts)
    patches = [(module, "run_to_end", run(module.run_to_end)) for module in modules]
    if not prepared:
        patches += [
            (scripts, "ensure_script_env", lambda state_dir: Path(state_dir) / "script-env"),
            (node_scripts, "ensure_node_env", lambda state_dir: Path(state_dir) / "node-env"),
            *((module, "for_scripts", lambda *args, **kwargs: None) for module in modules),
        ]
    originals = [(module, name, getattr(module, name)) for module, name, _ in patches]
    for module, name, value in patches:
        setattr(module, name, value)
    try:
        yield
    finally:
        for module, name, value in originals:
            setattr(module, name, value)


@contextlib.contextmanager
def recorded_models() -> Iterator[None]:
    """Each model's answers, and what each script printed, also go to the tape of the task that
    asked."""

    def build(original: Any) -> Any:
        def resolve(name: str, custom_providers: Any = None) -> Any:
            chat_model = original(name, custom_providers)
            chat_model.callbacks = [*(chat_model.callbacks or []), _Record()]
            return chat_model

        return resolve

    def run(original: Any) -> Any:
        def run_to_end(*args: Any, **kwargs: Any) -> Any:
            cwd = _cwd(args, kwargs)
            before = _workspace_files(cwd)
            ran = original(*args, **kwargs)
            tape = _current()
            if tape is not None:
                tape.add_script(ran, _written(cwd, before))
            return ran

        return run_to_end

    with _models(build), _scripts(run, prepared=True):
        yield


@contextlib.contextmanager
def taped_models() -> Iterator[None]:
    """No model is built and no script's interpreter started: every answer and every script's
    output comes from the running task's tape."""

    def build(original: Any) -> Any:
        return lambda name, custom_providers=None: TapeModel()

    def run(original: Any) -> Any:
        return lambda *args, **kwargs: _tape().next_script(_cwd(args, kwargs))

    with _models(build), _scripts(run, prepared=False):
        yield
