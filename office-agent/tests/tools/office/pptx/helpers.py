from pathlib import Path

from coscribe.tools.presentations import build_presentation_tools
from tests.libreoffice_probe import libreoffice_works


def _tools_by_name(root: Path) -> dict[str, object]:
    return {tool.__name__: tool for tool in build_presentation_tools(root)}  # type: ignore[attr-defined]


def _write_wav(path: Path, seconds: float = 1.0) -> None:
    """A minimal, real, valid WAV file (silence) -- stdlib `wave`, no
    external audio tooling needed."""
    import struct
    import wave

    frame_rate = 8000
    frame_count = int(frame_rate * seconds)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(frame_rate)
        wav_file.writeframes(b"".join(struct.pack("<h", 0) for _ in range(frame_count)))


def _libreoffice_actually_works() -> bool:
    return libreoffice_works()


TWO_SLIDE_CONTENT = """\
# Intro
- point one
- point two

---

# Data
| name | score |
| --- | --- |
| Alice | 9 |
| Bob | 7 |
"""


def _make_test_png(path: Path) -> None:
    from PIL import Image

    Image.new("RGB", (10, 10), color="red").save(path)


_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


_P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
