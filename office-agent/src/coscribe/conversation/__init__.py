"""One conversation: the session that runs a thread's turns, approvals and
history, and the small stores it reads. Used by the web server and the CLI,
which is why it does not live under web/ and knows nothing of HTTP: it talks to
whoever is connected through an EventSink."""

from .activity import OPENABLE_EXTENSIONS, open_in_os
from .artifact_files import ArtifactFileError, copy_file, rename_file, trash_file
from .artifacts import ArtifactRegistry, adopt_thread, describe_artifact
from .dashboard import DashboardDataError, is_dashboard, read_dashboard_data, render_dashboard
from .design_canvas import (
    CanvasError,
    canvas_folder,
    canvas_of_page,
    is_canvas,
    place_on_canvas,
    read_canvas,
    variables_style,
)
from .session import ChatSessionLG
from .thread_meta import ThreadMetaStore

__all__ = [
    "OPENABLE_EXTENSIONS",
    "ChatSessionLG",
    "ThreadMetaStore",
    "ArtifactFileError",
    "ArtifactRegistry",
    "adopt_thread",
    "copy_file",
    "rename_file",
    "trash_file",
    "describe_artifact",
    "CanvasError",
    "canvas_folder",
    "canvas_of_page",
    "is_canvas",
    "place_on_canvas",
    "read_canvas",
    "variables_style",
    "DashboardDataError",
    "is_dashboard",
    "read_dashboard_data",
    "render_dashboard",
    "open_in_os",
]
