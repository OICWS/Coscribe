"""The web as the model reaches it: the browser, web search and page reading, HTTP requests with
secret substitution, and licensed image search and download."""

from __future__ import annotations

from .browser import (
    BROWSER_HOST,
    SCREENSHOT_FOLDER,
    BrowserHost,
    BrowserUnavailableError,
    browser_run,
    build_browser_tools,
    page_screenshot,
)
from .http_request import build_http_tools
from .images import build_image_tools
from .websearch import build_websearch_tools

__all__ = [
    "BROWSER_HOST",
    "browser_run",
    "SCREENSHOT_FOLDER",
    "BrowserHost",
    "BrowserUnavailableError",
    "build_browser_tools",
    "build_http_tools",
    "build_image_tools",
    "build_websearch_tools",
    "page_screenshot",
]
