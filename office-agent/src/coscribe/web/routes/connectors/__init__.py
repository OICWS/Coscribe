"""Connectors routes: one module per resource."""

from __future__ import annotations

from fastapi import APIRouter

from ...state import AppState
from . import catalog, check, maintenance, oauth_apps, offers, permissions, servers, signin


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    for module in (catalog, oauth_apps, signin, servers, permissions, maintenance, check, offers):
        router.include_router(module.router(state))
    return router
