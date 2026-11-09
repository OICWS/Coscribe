"""A "webhook" task's address and key on the task page (decision 0040): the listener's address,
the key a program sends events with (only by POST, which needs the launch token), a new key, and
waiting for a sample event to map inputs from."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...tools import ScheduledTriggerStore
from ..schemas import WebhookKey, WebhookSample
from ..state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    listener = state.webhooks

    def _answer(trigger_id: str) -> JSONResponse:
        status = listener.status()
        store = ScheduledTriggerStore(settings.state_dir)
        return JSONResponse({**status, "url": status["url"] + trigger_id,
                             **store.webhooks.shown(trigger_id)})  # fmt: skip

    def _task(trigger_id: str) -> Any:
        try:
            trigger = ScheduledTriggerStore(settings.state_dir).load(trigger_id)
        except ValueError:
            return None
        return trigger if trigger is not None and trigger.schedule.kind == "webhook" else None

    def _missing(trigger_id: str) -> JSONResponse:
        return JSONResponse({"error": f"No task {trigger_id!r} starts on events"}, status_code=404)

    async def webhook(trigger_id: str) -> JSONResponse:
        # Reads only, and never the key: a GET needs no launch token, so any local program could.
        if _task(trigger_id) is None:
            return _missing(trigger_id)
        return _answer(trigger_id)

    async def key(trigger_id: str, payload: WebhookKey) -> JSONResponse:
        if _task(trigger_id) is None:
            return _missing(trigger_id)
        events = ScheduledTriggerStore(settings.state_dir).webhooks
        value = events.new_key(trigger_id) if payload.new else events.key(trigger_id)
        if value is None:
            # Never replaced on a read: senders that have the key would be refused unawares.
            error = "Its key couldn't be read from the keychain; make a new key"
            return JSONResponse({"error": error}, status_code=409)
        return JSONResponse({"key": value})

    async def sample(trigger_id: str, payload: WebhookSample) -> JSONResponse:
        if _task(trigger_id) is None:
            return _missing(trigger_id)
        store = ScheduledTriggerStore(settings.state_dir)
        store.webhooks.wait_for_sample(trigger_id, payload.waiting)
        return _answer(trigger_id)

    path = "/api/scheduled-tasks/{trigger_id}/webhook"
    router.add_api_route(path, webhook, methods=["GET"])
    router.add_api_route(f"{path}/key", key, methods=["POST"])
    router.add_api_route(f"{path}/sample", sample, methods=["POST"])
    return router
