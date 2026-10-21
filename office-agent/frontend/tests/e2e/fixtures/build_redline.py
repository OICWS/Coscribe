"""Builds a Word file with two tracked changes and a comment, for the Word panel spec:
`python build_redline.py <workspace> <name> [picture]` writes `<name>.docx`, with a picture when asked."""

import sys
from pathlib import Path

from coscribe.tools.office.document_tools import build_document_tools

CONTRACT = """\
# Service agreement

## Price

The total price is 100 dollars, due within 30 days of the invoice date. {{comment: Final price?}}

## Term

The agreement runs for one year.
"""

workspace, name = Path(sys.argv[1]), sys.argv[2]
tools = {tool.__name__: tool for tool in build_document_tools(workspace)}  # type: ignore[attr-defined]
tools["write_docx"](path=f"{name}.docx", content=CONTRACT, comment_author="Ana Lee")
tools["insert_docx_text"](path=f"{name}.docx", text=" (extended)", context_before="30 days")
tools["delete_docx_text"](path=f"{name}.docx", text="100 dollars")

if len(sys.argv) > 3 and sys.argv[3] == "picture":
    from PIL import Image

    Image.new("RGB", (120, 60), "tomato").save(workspace / f"{name}.png")
    tools["add_docx_image"](path=f"{name}.docx", image_path=f"{name}.png", after_text="runs for one year")
