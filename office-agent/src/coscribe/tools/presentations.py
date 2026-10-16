"""PowerPoint (.pptx) read/write tools, scoped to a single workspace root.

Mirrors ``tools/office/document_tools.py``/``office/xlsx`` -- same ``WorkspaceScope``
sandboxing, same shape (a toolkit class + a ``build_*_tools`` factory).

Unlike docx/pdf/xlsx, ``python-pptx`` (the library used here) hasn't had a
release since August 2024 -- it's the standard, complete-enough library for
this, not a "mature and audited" pick like the others. And unlike every
other tool in this package, ``write_pptx`` optionally has the office program
installed draw the deck as a PDF (decision 0012) and flags text that
overflows its slide bounds -- the single most common visual defect,
per Anthropic's own published pptx Skill notes (see ``ARCHITECTURE.md`` for
why we don't use that Skill directly: it's script-driven, and coscribe
has no code-execution tool). This is a *diagnostic*, not a requirement --
no office program, a timeout or a failed conversion just means the write
still succeeds with ``overflow_warnings: []`` and a ``qa_skipped_reason``
explaining why.

``content`` is markdown where a line containing exactly ``---`` separates
slides (the same convention Pandoc/Marp/reveal.js already use), reusing
``office/markdown_blocks.py``'s ``parse_blocks``/``Block`` per slide chunk: the first
heading becomes the slide title, remaining blocks become the body. A slide
may have a table *or* bullets/paragraphs, not both -- deliberately
constrained, like ``write_xlsx``'s per-sheet-overwrite rule.

``pdfplumber``/``pptx`` are imported lazily, inside each function that
actually needs them, rather than at module level -- same real, measured
startup-time reasoning as ``office/docx``'s identical change, see that
module's docstring and runtime_lg/README.md's startup-time section.
``PresentationType`` is only ever used as a type annotation (never at
runtime, thanks to ``from __future__ import annotations``), so it's
imported under ``TYPE_CHECKING`` instead of even a lazy runtime import.

``add_pptx_chart`` only builds through python-pptx's high-level
``CategoryChartData``/``add_chart`` API, never hand-written chart XML --
axis/series registration is correct by construction that way. Same
deliberate scoping as ``office/xlsx``'s ``add_xlsx_chart``: single-
purpose bar/line/pie charts only, no stacked or secondary-axis/combo
charts -- exactly the configurations Anthropic's own pptx skill documents
as producing schema-valid XML that PowerPoint silently treats as corrupt.
Restricting the feature surface avoids that failure class outright rather
than needing a post-hoc validator. Chart data is a pipe-table string, the
same convention ``write_xlsx`` already uses -- not a list/dict tool
parameter, which no tool in this package uses: tool-schema inference
has broken on less exotic type hints than that (see the
``Optional[int]``/``Optional[str]`` comments below and in
``office/xlsx``).

``add_pptx_image``/``set_pptx_notes`` and ``write_pptx``'s/``write_docx``'s
``template_path`` are all pure high-level python-pptx/python-docx API calls,
no raw XML. ``set_pptx_transition`` and ``add_pptx_animation`` are not --
python-pptx has no transition or animation API at all, so both hand-build
OOXML via ``lxml``. ``set_pptx_transition`` is low-risk hand-written XML
(the base ECMA-376 schema has a ``<p:transition>`` element; a fresh slide's
own children are verified to always be ``['cSld', 'clrMapOvr']``, so
appending at the end is always schema-correct here). ``add_pptx_animation``
is the riskiest thing in this file: its ``<p:timing>`` tree structure and
per-effect XML (``fade``/``fly-in``) are cross-checked against
``hugohe3/ppt-master``'s shipped, PowerPoint-authored
``pptx_animation_presets.json`` rather than written from memory, and the
saved file is re-opened and structurally verified before it's allowed to
replace the user's real file -- but that verification is structural, not
visual, since this sandbox has no real PowerPoint to test against, only
LibreOffice. See ``ARCHITECTURE.md`` for the full reasoning.

Every hand-XML write in this file (``set_pptx_transition``,
``add_pptx_animation``, ``edit_pptx_theme_colors``, and the theme-blob
edits inside ``write_pptx``/``fill_pptx_template`` for ``theme=``/CJK-font
handling) also runs through ``_ooxml_validate.assert_ooxml_valid`` before
the mutated element is ever serialized into the file -- a real ECMA-376
schema check (see ``_ooxml_schemas/NOTICE.md``), not just the
application-level checks above. This catches what those checks aren't
designed to: a structurally wrong OOXML document that happens to still
satisfy a narrower "did my specific edit land" check, or that ``prs.save()``
and LibreOffice's own more forgiving parser would silently accept anyway.
"""

from __future__ import annotations

from .office.pptx.tool_wrappers import build_presentation_tools
from .office.pptx.toolkit import PresentationToolkit

__all__ = ["PresentationToolkit", "build_presentation_tools"]
