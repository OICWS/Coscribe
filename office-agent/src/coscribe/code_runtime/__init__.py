"""The code module: Codex (openai/codex) run as coscribe's second agent
runtime, downloaded on demand and driven through `codex app-server`. See
ROADMAP.md's Codex entry for why it is shaped this way."""

from .install import CodexUnavailable
from .launch import codex_model
from .permissions import CodePermissions
from .service import CodeService, code_service, remove_stale_code_sidecars, shutdown_code_services
from .thread import ApprovalRequest, CodexEvent, CodexThread, shell_script

__all__ = [
    "ApprovalRequest",
    "CodePermissions",
    "CodeService",
    "CodexEvent",
    "CodexThread",
    "CodexUnavailable",
    "code_service",
    "codex_model",
    "remove_stale_code_sidecars",
    "shell_script",
    "shutdown_code_services",
]
