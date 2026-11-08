"""The listener a program on this machine sends a task's events to (decision 0040): its own server
on 127.0.0.1 and a fixed port, so the address stays the same across launches and the main server's
launch-token guard stays as it is. It answers `POST /hooks/<task id>` and nothing else, and runs
only while a task that starts on events is on."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import sys
from collections.abc import Callable, Coroutine
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..config import Settings
from ..runtime_lg import AuditLog, record_decision
from ..tools import SCHEDULED_THREAD_PREFIX, ScheduledRun, ScheduledTriggerStore
from ..workflows import parse_workflow

logger = logging.getLogger(__name__)

# Bytes, so a body is refused before it is read whole; the event is checked again as text.
MAX_BODY = 64_000

Started = Callable[[str, str, list[ScheduledRun]], Coroutine[Any, Any, None]]


def _answer(status: int, message: str, **extra: Any) -> JSONResponse:
    key = "error" if status >= 400 else "message"
    return JSONResponse({key: message, **extra}, status_code=status)


async def _body(request: Request) -> bytes | None:
    """The body, or None once it is over MAX_BODY, whatever Content-Length said."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY:
            return None
    return bytes(body)


class WebhookListener:
    def __init__(self, settings: Settings, started: Started) -> None:
        self._settings = settings
        self._started = started
        self._server: uvicorn.Server | None = None
        self._serving: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self.port: int | None = None
        self.error: str | None = None

    def status(self) -> dict[str, Any]:
        """Where events go, for the task page: the port it listens on, or why it doesn't."""
        port = self.port or self._settings.webhook_port
        listening = self._server is not None and not self._server.should_exit
        return {"url": f"http://127.0.0.1:{port}/hooks/", "listening": listening,
                "error": self.error}  # fmt: skip

    def _wanted(self) -> bool:
        store = ScheduledTriggerStore(self._settings.state_dir)
        tasks = [t for t in store.list_all() if t.schedule.kind == "webhook"]
        # Made here, where every save of a task passes, so the task page only reads it.
        for task in tasks:
            store.webhooks.ensure_key(task.trigger_id)
        return any(t.enabled for t in tasks)

    async def sync(self) -> None:
        """Listen while a task that starts on events is on, and only then; each has a key."""
        async with self._lock:
            wanted = self._wanted()
            if wanted and self._server is None:
                self._start()
            elif not wanted and self._server is not None:
                await self._stop()

    async def stop(self) -> None:
        async with self._lock:
            await self._stop()

    def _start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sys.platform == "win32":
            # No other program may take the port while it is ours, even one asking to share it.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            # The port comes back at once after a stop, not when its last connections time out.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Taken here, not by uvicorn, which exits the process when a port is busy.
            sock.bind(("127.0.0.1", self._settings.webhook_port))
        except OSError as exc:
            sock.close()
            self.error = (f"Port {self._settings.webhook_port} is taken by another program "
                          f"({exc.strerror}); pick another in Settings > Sessions")  # fmt: skip
            logger.warning("webhook: %s", self.error)
            return
        sock.listen()
        self.port, self.error = sock.getsockname()[1], None
        app = Starlette(routes=[Route("/hooks/{trigger_id}", self._receive, methods=["POST"])])
        config = uvicorn.Config(app, log_level="warning", lifespan="off", access_log=False)
        self._server = uvicorn.Server(config)
        self._serving = asyncio.create_task(self._server.serve(sockets=[sock]))

    async def _stop(self) -> None:
        if self._server is None or self._serving is None:
            return
        self._server.should_exit = True
        await asyncio.gather(self._serving, return_exceptions=True)
        self._server, self._serving, self.port = None, None, None

    async def _receive(self, request: Request) -> JSONResponse:
        if "origin" in request.headers:
            # A page in a browser always says where it comes from; a program on the machine doesn't.
            return _answer(403, "Events come from programs on this machine, not from web pages")
        trigger_id = request.path_params["trigger_id"]
        store = ScheduledTriggerStore(self._settings.state_dir)
        try:
            trigger = store.load(trigger_id)
        except ValueError:
            trigger = None
        scheme, _, key = request.headers.get("authorization", "").partition(" ")
        if (trigger is None or trigger.schedule.kind != "webhook" or scheme.lower() != "bearer"
                or not store.webhooks.accepts(trigger_id, key.strip())):  # fmt: skip
            # The same answer for a task that isn't there, so a wrong key says nothing about it.
            return _answer(401, "No task takes events with this key")
        if not trigger.enabled:
            return _answer(409, "The task is paused")
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            return _answer(415, "Send the event as JSON (Content-Type: application/json)")
        body = await _body(request)
        if body is None:
            return self._audit(trigger_id, MAX_BODY, _answer(413, "It is over 64 KB"))
        try:
            event = json.loads(body)
        except ValueError:
            return self._audit(trigger_id, len(body), _answer(400, "The body isn't JSON"))
        # Loaded again: another event may have started a run while this one was read.
        trigger = store.load(trigger_id) or trigger
        specs = list(parse_workflow(trigger.workflow or {}).inputs)
        delivery = store.webhooks.take(trigger_id, trigger.schedule, specs, trigger.runs, event)
        if delivery.inputs is None:
            return self._audit(trigger_id, len(body), _answer(delivery.status, delivery.message))
        _, run, pruned = store.start_run(trigger_id, "webhook", delivery.inputs, {"item": event})
        await self._started(trigger_id, run.run_id, pruned)
        answer = _answer(delivery.status, delivery.message, run=run.run_id)
        return self._audit(trigger_id, len(body), answer)

    def _audit(self, trigger_id: str, size: int, answer: JSONResponse) -> JSONResponse:
        # Never the body: it may hold anything, and the run keeps it where the person can see it.
        record_decision(
            AuditLog(self._settings.state_dir),
            thread_id=f"{SCHEDULED_THREAD_PREFIX}{trigger_id}",
            tool_name="webhook",
            arguments={"bytes": size},
            decision="approve" if answer.status_code < 300 else "reject",
            reason="webhook_event",
            detail=f"{answer.status_code} {bytes(answer.body).decode()[:300]}",
        )
        return answer
