"""Asking a connector's tool once, as a task that starts on its new items would (decision 0039), so
the task form can show what it finds and which fields an input can take."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ....tools import ScheduledTriggerStore, connector_of, is_read_only
from ....workflows import ask_connector
from ...schemas import ConnectorCheck
from ...state import AppState

# What the form lists of an answer; the rest is counted.
_SHOWN = 5
_CHECK_SECONDS = 60


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    _session_extra_tools = state.session_extra_tools
    items = ScheduledTriggerStore(state.settings.state_dir).connector_items

    async def check_connector_tool(payload: ConnectorCheck) -> JSONResponse:
        tool = next((t for t in _session_extra_tools()
                     if connector_of(t) is not None and t.name == payload.tool), None)  # fmt: skip
        if tool is None:
            message = f"{payload.tool} isn't available: connect it, or unblock it in Settings"
            return JSONResponse({"error": message}, status_code=404)
        read_only = is_read_only(tool)
        if not read_only and not payload.trust_unmarked:
            # Not even once: calling a tool that may change something is the person's choice.
            return JSONResponse({"read_only": False, "items": None})
        answer, error = await ask_connector(tool, payload.args, _CHECK_SECONDS)
        if error is not None:
            return JSONResponse({"read_only": read_only, "error": error})
        preview = items.preview(answer, _SHOWN)
        if preview is None:
            return JSONResponse(
                {"read_only": read_only, "error": "Its answer isn't a list of items"}
            )
        return JSONResponse({"read_only": read_only, **preview})

    router.add_api_route("/api/mcp/check", check_connector_tool, methods=["POST"])
    return router
