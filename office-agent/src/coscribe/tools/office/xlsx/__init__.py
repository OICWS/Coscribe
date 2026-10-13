"""Excel (.xlsx) read/write tools, scoped to a single workspace root.

Mirrors ``tools/office/document_tools.py``'s docx/pdf tools -- same ``WorkspaceScope``
sandboxing, same reasoning for being a built-in tool rather than an MCP
server (``openpyxl`` is just as mature/audited as ``python-docx``/
``pdfplumber``, and there's no more authoritative Excel MCP server than the
personally-maintained niche repos already rejected for Word/PDF -- see
``ARCHITECTURE.md``).

Unlike docx/pdf, a workbook is a *grid*, not flowing text, so ``write_xlsx``
only accepts pipe-table rows (reusing ``office/markdown_blocks.py``'s row-parsing
helpers), not the full heading/bullet/paragraph markdown subset. And
``overwrite`` here is scoped to *the named sheet*, not the whole file --
see ``write_xlsx``'s docstring -- since building up a multi-sheet workbook
across several calls is the one thing that meaningfully differs about
spreadsheets versus the one-shot documents in ``office/docx``.

``openpyxl`` is imported lazily, inside each method that actually needs
it, rather than at module level -- same real, measured startup-time
reasoning as ``office/docx``'s identical change, see that module's
docstring and runtime_lg/README.md's startup-time section. ``Worksheet``
is only ever used as a type annotation, so ``helpers.py`` imports it under
``TYPE_CHECKING`` instead of even a lazy runtime import.

``add_xlsx_chart`` only builds through openpyxl's high-level chart
classes (``BarChart``/``LineChart``/``PieChart`` + ``Reference``), never
hand-written chart XML -- axis/series registration is correct by
construction that way. Deliberately scoped to single-purpose bar/line/pie
charts, no stacked or secondary-axis/combo charts: those are exactly the
configurations Anthropic's own pptx skill (referenced in
``ARCHITECTURE.md``) documents as producing schema-valid XML that Excel/
PowerPoint silently treats as corrupt (a stacked bar's data-label position,
a combo chart's under-declared secondary axis). Restricting the feature
surface avoids that failure class outright rather than needing a
validator to catch it after the fact.

``write_xlsx`` writes formula strings (``"=SUM(A2:B2)"``) as real Excel
formulas -- openpyxl already does this for any cell string starting with
``=``, no special handling needed there. What *is* handled explicitly,
cross-checked against Anthropic's own published xlsx skill rather than
guessed: (1) a hard block on ``SORT``/``FILTER``/``UNIQUE``/``SEQUENCE``
(``_xlsx_unsupported_functions``' own comment has the real reasoning --
these "dynamic array" functions need Excel-365-only OOXML machinery this
package doesn't write yet); (2) auto-prefixing the post-2007 functions
Excel stores with a hidden ``_xlfn.`` prefix (``TEXTJOIN``/``CONCAT``/
``IFS``/``SWITCH``/``MAXIFS``/``MINIFS``/``XLOOKUP``/``XMATCH``) --
written bare, each evaluates to ``#NAME?`` in the saved file, so the
model doesn't need to remember this Excel/OOXML wrinkle itself. After
writing, ``_recalc_xlsx`` force-recalculates the whole workbook via a
LibreOffice macro (the same ``ThisComponent.calculateAll() + store() +
close()`` technique the xlsx skill's own ``recalc.py`` uses -- plain
``--convert-to`` does NOT force recalculation, only a macro does, verified
empirically here) and reports any Excel error strings (``#DIV/0!`` etc.)
found afterward. Without this, every formula cell openpyxl just wrote
reads back as ``None`` to ``read_xlsx``/anything using ``data_only=True``
until the user happens to open the file in real Excel -- a real,
confirmed gap this closes.

``XLOOKUP``/``XMATCH`` are the two exceptions LibreOffice still can't
compute, but *aren't* hard-blocked -- their common scalar usage (one
lookup value, one result -- as opposed to a lookup value spanning
multiple cells, or a multi-column ``return_array``, both real Excel
usages this module declines rather than guesses at) needs no spill
metadata at all, so ``_xlsx_lookup_formulas.py`` evaluates them itself
and patches a real cached value straight into the saved worksheet XML --
``_recalc_xlsx_and_evaluate_lookups`` is the combined entry point
``write_xlsx``/``edit_xlsx_cells``/``recalc_xlsx`` all call instead of
``_recalc_xlsx`` directly. See that module's own docstring for why direct
XML patching is necessary (openpyxl has no API to write *any* formula
cell's cached value, confirmed by reading its writer source) and exactly
how narrowly it's scoped (declines anything beyond a single top-level
call with literal/plain-reference arguments, same as this file's own
"fail loudly, don't guess" formula-safety posture).

``merge_xlsx_cells``/``unmerge_xlsx_cells``/``add_xlsx_conditional_format``/
``set_xlsx_data_validation``/``freeze_xlsx_panes``/``set_xlsx_column_width``/
``edit_xlsx_cells`` fill gaps found by cross-referencing this file against
Anthropic's own xlsx skill a second time (the same discipline the formula
handling above already used): merged cells ("write the top-left anchor
only", already true of how ``format_xlsx_cells``' range-flattening
handles a merged range -- openpyxl itself makes every non-anchor cell a
read-only ``MergedCell``), conditional formatting, data validation,
freeze panes, and column widths were all named in that skill but had no
tool here at all; ``write_xlsx``'s whole-sheet replace was also the one
thing on this file's own backlog (see this package's own design log,
``ROADMAP.md``) -- ``edit_xlsx_cells`` writes only the addressed block,
leaving the rest of the sheet (other cells, formatting, merges, charts)
untouched, reusing ``write_xlsx``'s own pipe-table parsing/formula
validation rather than duplicating it. ``merge_xlsx_cells`` explicitly
rejects a range that overlaps an already-merged one -- confirmed
empirically that openpyxl's own ``merge_cells`` does *not* raise on this
(it silently accepts a corrupt-looking double-merge), so this tool adds
the check openpyxl itself skips.
"""

from __future__ import annotations

from .toolkit import SpreadsheetToolkit
from .tools import build_spreadsheet_tools

__all__ = ["SpreadsheetToolkit", "build_spreadsheet_tools"]
