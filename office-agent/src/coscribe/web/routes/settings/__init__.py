"""Settings routes: one module per resource."""

from __future__ import annotations

from fastapi import APIRouter

from ...state import AppState
from . import (
    catalog,
    code,
    config,
    design_systems,
    environments,
    libreoffice,
    memory,
    named_environments,
    providers,
    proxy,
    secrets,
)


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    modules = (catalog, config, code, secrets, memory, providers, environments, named_environments)
    for module in (*modules, design_systems, libreoffice, proxy):
        router.include_router(module.router(state))
    return router
