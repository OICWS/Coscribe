"""A Dashboard artifact's source: an `.html` page marked as a dashboard and, in the folder beside
it, the datasets it shows. It sits with the artifact registry, the one other reader of it. The page
writes no figure itself; the app serves it with its datasets and the chart library put into it,
because the frame it is drawn in has no network.

    sales.html              <meta name="coscribe" content="dashboard"> in its head
    sales.dashboard         the folder beside it, holding
      datasets.json         {"datasets": {id: {title, source, updated, columns}},
                             "figures": {id: {label, value, formula, from}}}
      data/<id>.json        the rows: objects, or {"columns": [...], "rows": [[...]]}
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_NAME = rb"name\s*=\s*[\"']coscribe[\"']"
_CONTENT = rb"content\s*=\s*[\"']dashboard[\"']"
_MARKER = re.compile(
    rb"<meta\s+(?:" + _NAME + rb"\s+" + _CONTENT + rb"|" + _CONTENT + rb"\s+" + _NAME + rb")",
    re.IGNORECASE,
)
# The marker belongs in the head; a page is not read further to find it.
_HEAD_BYTES = 8192
_LIBRARY_TAG = re.compile(
    rb"<script\b[^>]*\bdata-coscribe-lib\s*=\s*[\"']d3[\"'][^>]*>\s*</script>", re.I
)
_HEAD_OPEN = re.compile(rb"<head\b[^>]*>", re.IGNORECASE)
_BODY_CLOSE = re.compile(rb"</body\s*>", re.IGNORECASE)
_SOURCES = Path(__file__).with_name("dashboard_sources.js")
_VENDOR = Path(__file__).parent / "_vendor"
# What the page and its data may weigh together, as a design page may.
MAX_DATA_BYTES = 8 * 1024 * 1024


class DashboardDataError(ValueError):
    """The datasets beside a dashboard cannot be read; the text is safe to show."""


def is_dashboard(page: bytes) -> bool:
    return _MARKER.search(page[:_HEAD_BYTES]) is not None


def dashboard_folder(page: Path) -> Path:
    return page.with_name(f"{page.stem}.dashboard")


def _rows(raw: Any, dataset: str) -> list[dict[str, Any]]:
    if isinstance(raw, list) and all(isinstance(row, dict) for row in raw):
        return raw
    if (
        isinstance(raw, dict)
        and isinstance(raw.get("columns"), list)
        and isinstance(raw.get("rows"), list)
    ):
        columns = [str(c) for c in raw["columns"]]
        if all(isinstance(row, list) and len(row) == len(columns) for row in raw["rows"]):
            return [dict(zip(columns, row, strict=True)) for row in raw["rows"]]
    raise DashboardDataError(
        f"data/{dataset}.json is neither a list of rows nor columns with rows of the same length"
    )


def read_dashboard_data(page: Path) -> dict[str, Any]:
    """The datasets and figures the page shows, each dataset with its rows; empty when the page has
    no folder yet."""
    folder = dashboard_folder(page)
    index = folder / "datasets.json"
    if not index.is_file():
        return {"datasets": {}, "figures": {}}
    try:
        manifest = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DashboardDataError(f"{folder.name}/datasets.json is not valid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise DashboardDataError(f"{folder.name}/datasets.json is not an object")
    declared = manifest.get("datasets") or {}
    figures = manifest.get("figures") or {}
    if not isinstance(declared, dict) or not isinstance(figures, dict):
        raise DashboardDataError("datasets and figures are objects keyed by their id")
    total = index.stat().st_size
    datasets: dict[str, Any] = {}
    for name, info in declared.items():
        data = folder / "data" / f"{name}.json"
        if not isinstance(info, dict) or not re.fullmatch(r"[\w-]+", name):
            raise DashboardDataError(f"Dataset {name!r} needs a plain id and an object")
        rows: list[dict[str, Any]] = []
        if data.is_file():
            total += data.stat().st_size
            if total > MAX_DATA_BYTES:
                raise DashboardDataError("The dashboard's data is larger than 8 MB")
            try:
                rows = _rows(json.loads(data.read_text(encoding="utf-8")), name)
            except (OSError, ValueError) as exc:
                if isinstance(exc, DashboardDataError):
                    raise
                raise DashboardDataError(f"data/{name}.json is not valid JSON: {exc}") from exc
        datasets[name] = {**info, "rows": rows}
    return {"datasets": datasets, "figures": figures}


def _script(code: bytes) -> bytes:
    return b"<script>" + code + b"</script>"


def _json_script(name: str, value: Any) -> bytes:
    # Inside a script element only "</" can end it early, and in JSON it can only sit in a string,
    # where "<\/" reads the same.
    text = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return _script(f"window.{name}={text};".encode())


def render_dashboard(page: Path, body: bytes) -> bytes:
    """The page with `window.coscribe` (its datasets and figures) set before its own scripts run,
    d3 where the page asks for it with `<script data-coscribe-lib="d3"></script>`, and at its end
    what lets a reader see where a figure or chart came from. A page whose
    data cannot be read is served with the reason in `window.coscribe.error`, so it can say so."""
    try:
        payload: dict[str, Any] = read_dashboard_data(page)
    except DashboardDataError as exc:
        payload = {"datasets": {}, "figures": {}, "error": str(exc)}
    data = _json_script("coscribe", payload)
    if _LIBRARY_TAG.search(body):
        # The vendored file holds no "</", so it goes in as it is.
        library = (_VENDOR / "d3.min.js").read_bytes()
        body = _LIBRARY_TAG.sub(lambda _: _script(library), body, count=1)
    head = _HEAD_OPEN.search(body)
    at = head.end() if head else 0
    body = body[:at] + data + body[at:]
    # After the page's own scripts, so what they drew is there to point at.
    sources = _script(_SOURCES.read_bytes())
    end = _BODY_CLOSE.search(body)
    return body[: end.start()] + sources + body[end.start() :] if end else body + sources
