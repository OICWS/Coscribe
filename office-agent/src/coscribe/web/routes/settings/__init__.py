"""Settings routes: one module per resource."""

from __future__ import annotations

from fastapi import APIRouter

from ...state import AppState
from . import catalog, code, config, environments, memory, providers, secrets


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    for module in (catalog, config, code, secrets, memory, providers, environments):
        router.include_router(module.router(state))
    return router
