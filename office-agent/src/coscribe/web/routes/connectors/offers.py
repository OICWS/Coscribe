""" "Not now" on a connector the conversation offered in the chat (decision 0046). Connecting
happens in Settings > Connectors like any other connection; `carry_on_offers` then wakes the
conversation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ....conversation import OfferLog
from ...state import AppState


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    log = OfferLog(state.settings.state_dir)

    async def decline_offer(thread_id: str, name: str) -> dict[str, Any]:
        if log.state(thread_id, name) != "offered":
            return {"declined": False}
        log.mark(thread_id, name, "declined")
        return {"declined": True}

    router.add_api_route(
        "/api/threads/{thread_id}/connector-offers/{name}/decline", decline_offer, methods=["POST"]
    )
    return router
