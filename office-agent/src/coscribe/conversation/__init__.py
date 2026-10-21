"""One conversation: the session that runs a thread's turns, approvals and
history, and the small stores it reads. Used by the web server and the CLI,
which is why it does not live under web/ and knows nothing of HTTP: it talks to
whoever is connected through an EventSink."""

from .activity import OPENABLE_EXTENSIONS, open_in_os
from .artifacts import ArtifactRegistry, adopt_thread, describe_artifact
from .session import ChatSessionLG
from .thread_meta import ThreadMetaStore

__all__ = [
    "OPENABLE_EXTENSIONS",
    "ChatSessionLG",
    "ThreadMetaStore",
    "ArtifactRegistry",
    "adopt_thread",
    "describe_artifact",
    "open_in_os",
]
