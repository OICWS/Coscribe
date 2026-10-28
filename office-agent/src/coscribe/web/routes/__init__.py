"""The server's routes, one module per area; each builds its router from the shared AppState."""

from fastapi import FastAPI

from ..state import AppState
from .artifacts import router as artifacts_router
from .connectors import router as connectors_router
from .design import router as design_router
from .doc import router as doc_router
from .files import router as files_router
from .internal import router as internal_router
from .scheduled import router as scheduled_router
from .settings import router as settings_router
from .skills import router as skills_router
from .slides import router as slides_router
from .threads import router as threads_router
from .ws import router as ws_router


def include_routers(app: FastAPI, state: AppState) -> None:
    # The order is the order the routes are matched in; `tests/web_routes.txt` pins it.
    for build_router in (
        internal_router,
        threads_router,
        slides_router,
        artifacts_router,
        doc_router,
        design_router,
        scheduled_router,
        settings_router,
        skills_router,
        files_router,
        connectors_router,
        ws_router,
    ):
        app.include_router(build_router(state))
