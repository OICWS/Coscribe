# Property tests for the XLOOKUP/XMATCH evaluator (shipped)

Why: issue #149. `tools/_xlsx_lookup_formulas.py` computes `XLOOKUP` and `XMATCH` for workbooks because LibreOffice cannot, and the Excel phase of decision 0010 will lean on it. Example tests cannot show it agrees with Excel on inputs nobody thought of.

## Shipped
- `office-agent/tests/test_xlsx_lookup_formulas_properties.py`, 13 Hypothesis properties (`derandomize=True`, `deadline=None`, 100 examples; 25 for the ones that write a file; 5 for LibreOffice). Whole file runs in about 15 s with LibreOffice.
- What the module supports, and so what is tested: `XLOOKUP` (3 to 6 arguments) and `XMATCH` (2 to 4), as the whole formula of a cell, with arguments that are literals (text, number, TRUE/FALSE) or plain references (`A2`, `A2:B9`, `A:A`, `2:2`, `'My Sheet'!B:B`); `match_mode` -1, 0, 1, 2 (wildcard); `search_mode` 1, -1, 2, -2; an optional `_xlfn.` / `_xlfn._xlws.` prefix. It has no `INDEX`/`MATCH` and no formula printer, so the round trip tested is `parse_single_call` over generated argument lists.
- Properties: the match index against a plain-Python reference (exact, first or last hit; nearest number below or above; wildcard against `fnmatch`; sorted keys against `bisect`); `evaluate_formula` over generated sheets (options, fallback, whole-column references, invalid options, mismatched ranges); the patched file read back (value, cell type, sheet choice); parsing; a formula that is not one call is declined; a recalculation in LibreOffice (`real_libreoffice`) where each call is paired with the `INDEX`/`MATCH` formula LibreOffice computes (LibreOffice 24.2 has no `XLOOKUP`).
- Each property was shown to catch a break in the module, listed in the PR.
- Found while writing them, not fixed (no change under `src/`): #156 (one-cell range gives `#VALUE!`), #157 (empty result cell written as the text `None`), #158 (text with `match_mode` -1/1 is exact only), #159 (two calls joined by an operator read as one). The generators avoid exactly these inputs.

## Not verified
- Excel itself: the reference is Excel's documented behaviour and LibreOffice's `INDEX`/`MATCH`, not a run in Excel.
- Windows: the tests are platform independent and run in the Linux CI job; the LibreOffice property skips where LibreOffice is not usable.

## Follow-ups
- Fix #156 to #159, then widen the generators (table size 1, empty result cells, text with `match_mode` -1/1, quoted boundary arguments).
- Move the import line when `spreadsheets.py` moves into `tools/office/` (#147): the file imports `coscribe.tools._xlsx_lookup_formulas` and `coscribe.tools.spreadsheets` once each.
