"""Word (.docx) read/write/edit tools, scoped to a single workspace root.

(The PDF tools live in `office/pdf/`; `office/document_tools.py` assembles both.)

Both writers accept the same lightweight markdown subset (headings via
``#``/``##``/``###``, ``-``/``*`` bullets, ``1.`` numbered items, and
``| a | b |`` pipe tables) so the model can produce either format from one
mental model. Editing an existing document is read -> modify the text ->
write(overwrite=True), the same whole-file-overwrite contract
``write_file`` already uses.

``read_docx`` converts via ``mammoth`` (docx -> html) + ``markdownify``
(html -> markdown) rather than walking the document tree by hand -- the
same pair of well-established libraries microsoft/markitdown itself uses
for docx, without markitdown's own mandatory ``magika`` dependency (which
drags in onnxruntime + numpy for file-type sniffing this codebase doesn't
need, since each tool already knows its own format). Its output is real
markdown -- a superset of the writers' subset (arbitrary heading depth,
links, bold/italic) -- rather than an exact mirror of what the writers
accept, so round-tripping a generated file through read_docx won't be
byte-for-byte identical, just semantically equivalent. ``read_pdf``/
``search_pdf`` (``office/pdf/``) extract text with ``pypdfium2``.

``mammoth``/``pypdfium2``/``docx``/``markdownify``/``reportlab`` are all
imported lazily, inside each method that actually needs them, rather than
at module level -- a real, measured startup-time cost (see
runtime_lg/README.md's startup-time section): every one of these tools is
registered into the Coordinator's tool list at agent-build time
regardless of whether it's ever called this session (the model needs
every tool's name/docstring/schema up front), but none of their
*implementations* are needed until a specific tool is actually invoked.
None of the tool-facing function signatures below reference any of these
libraries' own types (only `str`/`int`/`dict`/`list`), so LangChain's
tool-schema introspection never forces the lazy import open -- confirmed
by the docx tests still passing with these deferred.

``write_docx``'s optional ``template_path`` loads an existing .docx as the
starting point instead of a blank ``Document()``, then clears its body --
keeping only ``sectPr`` (page size/margins), removing every other child --
before writing the new content. Verified empirically (round-tripped
through python-docx) that removing anything else, or removing ``sectPr``
too, breaks the document; this is the one thing in this package that isn't a
pure library call.

``write_docx`` validates its finished in-memory document tree against the
real ECMA-376 ``wml.xsd`` schema (``_ooxml_validate.assert_wml_valid``)
immediately before ``document.save()`` -- the same "never serialize an
unvalidated write" discipline ``presentations.py`` already established
for its own hand-built OOXML (tracked-changes markup, TOC field,
comment-range anchors, and template body-clearing are all hand-mutated
XML python-docx has no schema-checked API for). A failure raises before
the file is touched, rather than producing a `.docx` that happens to open
in Word/LibreOffice's own forgiving parsers today but is not actually a
conformant document.

``insert_docx_text``/``delete_docx_text``/
``replace_docx_text``/``accept_docx_tracked_changes``/
``reject_docx_tracked_changes`` edit an *existing* docx in place with real
``<w:ins>``/``<w:del>`` tracked-changes markup, using
``_native_docx_tracks.tracks.TracksMixin`` (vendored from
`SecurityRonin/docx-mcp`, MIT -- see that package's NOTICE.md) for the
hard part: cascading context-anchored fuzzy text matching, multi-run-
spanning delete/insert with ``rPr`` inheritance, and word-level diff-
minimised replace. Unlike that project's own tool surface (which
addresses a paragraph by its ``w14:paraId``, discovered via a separate
call), these tools locate the target paragraph themselves from the text
being edited -- ``_locate_paragraph`` tries every paragraph and requires
exactly one unambiguous match -- so the caller never needs to know or
pass a paragraph id. ``_ensure_para_ids`` assigns a ``w14:paraId`` (a
Word 2010+ extension the vendored mixin's own paragraph lookup is keyed
on) to every paragraph that doesn't already have one -- real Word always
sets this, ``python-docx`` never does -- and marks the namespace
``mc:Ignorable`` on the document root the same way real Word-authored
files do, so the new attribute validates against ``wml.xsd`` the same
way any other Word 2010+ extension already does (see
``_ooxml_validate.py``'s ``_strip_mce_ignorable``).
"""

from __future__ import annotations

from .blocks import BlocksRefused, DocChanged, read_doc_blocks, save_doc_blocks
from .toolkit import DocxToolkit
from .tools import build_docx_tools

__all__ = [
    "BlocksRefused",
    "DocChanged",
    "DocxToolkit",
    "build_docx_tools",
    "read_doc_blocks",
    "save_doc_blocks",
]
