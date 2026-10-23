"""The one lock around PDFium. The library is not thread-safe: two threads rendering or reading
at once crash the whole process (a segmentation fault, which takes the server with it), and the
Slides panel asks for every thumbnail at the same time, so every caller holds this lock for as long
as it has a PDFium document open."""

from __future__ import annotations

import threading

PDFIUM_LOCK = threading.RLock()
