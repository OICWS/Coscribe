# XLOOKUP/XMATCH evaluator: four disagreements with Excel fixed (shipped)

Why: the property tests of #149 found four inputs where `tools/_xlsx_lookup_formulas.py` disagreed with Excel and LibreOffice; #156 to #159 tracked them, and board #168 assigned the fixes.

## Shipped
- #156: a reference to one cell is a one-element range in the lookup and return positions (`XLOOKUP("a",A1:A1,B1:B1)` returned `#VALUE!`); in the value, fallback and option positions it is still that cell's value.
- #157: an empty matched result cell is 0, as in Excel and LibreOffice's `INDEX`, not the text `None`.
- #158: with `match_mode` -1 or 1 a text lookup value finds the nearest text (case-insensitive) on the requested side; numbers and text never compare with each other.
- #159: `parse_single_call` declines a text whose parentheses close before the final `)`, so `F(a)&F(b)` is not read as one call with odd arguments.
- Each fix has a plain test of the smallest example (`tests/test_xlsx_lookup_formulas.py`; all four fail on `main`) and the property generators no longer avoid the input: tables of one row, empty result cells, text in approximate modes, and both quoted boundary arguments of two joined calls. The LibreOffice property gained pairs for text approximate matches, an empty result cell and a one-cell range; it fails on `main` for the text pair.

## Not verified
- Excel itself. Text ordering is case-insensitive code point order; Excel's collation of punctuation and non-ASCII letters may differ, and LibreOffice's was only checked on the letters a, b.

## Follow-ups
- None.
