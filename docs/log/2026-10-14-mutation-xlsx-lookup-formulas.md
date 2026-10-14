# Mutation survivors of `tools/_xlsx_lookup_formulas.py` killed or explained (shipped)

Why: the nightly mutation run left 225 survivors in the native `XLOOKUP`/`XMATCH` evaluator, the code that writes a cached value into the user's workbook (#227, part of #165).

## Shipped
- `tests/test_xlsx_lookup_formulas.py`, 280 tests (was 22): where an argument list splits and when it stops being one call; every spelling of the function name; literals and references (sheets, `$`, whole columns and rows, multi-digit rows); Excel equality and wildcards; the nearest-match search in both directions and with ties; every match and search mode, its default and its `#VALUE!`/`#N/A` result; which one-cell references become a single value; the type and text written for each kind of result; the sheet-to-file mapping; and whole-file runs (cached values of formula cells in a lookup range, a formula that cannot be evaluated next to ones that can, an array formula, the parts of the archive left untouched).
- `python scripts/mutation.py run xlsx_lookup_formulas --out DIR` (mutmut 3.8.0, Linux): before, 529 of 758 caught (the numbers in #227); after, `{"mutants": 758, "killed": 712, "survived": 40, "timeout": 6, "no_tests": 0}`, so 718 caught. No change under `src/`.

| Group | Mutants | Why the behaviour cannot differ |
|---|---|---|
| `None` for `False`, or `None` for `""`, as the start value of a flag (`in_quotes`, `in_sheet_name`, `quote`) | 5 | each is only ever tested for truth |
| An escaped `""` not recognised in `_split_top_level_args` (`i + 2 < n`, comparing with `XX"XX`) | 2 | closing and at once reopening the quote leaves the same state and the same text |
| `"\"'"` to `"XX\"'XX"` in `_is_one_argument_list` | 1 | a one-character test against a string that still holds both quotes |
| `or ""` to `or "XXXX"` after `match.group("ref")` | 1 | the group always matched, so the default is never used |
| `and` to `or` between `isalpha()`/`isdigit()` of the two ends of a range | 2 | the pattern only allows both ends of the same kind |
| The four `is None` tests on `range_boundaries` | 3 | that call returns four numbers for every form the pattern allows |
| `and` to `or` in `_excel_eq` (bool test, number test) | 2 | the other branches return the same False for those pairs |
| `<=` for `<` and `>=` for `>` in `_nearest_index` | 2 | an equal value has already returned |
| Default `search_mode` 2 for 1 (`XMATCH`, `XLOOKUP`) | 2 | both scan forward |
| `cast(None, ...)` | 2 | `typing.cast` returns its argument unchanged at run time |
| `iter(None)` for a tag filter in `_sheet_archive_paths` and `_patch_cell`; `if rel_id` forced true | 4 | the extra elements it visits have no `name`, `Id` or matching `r` |
| The `elif "t" in cell_el.attrib` branch of `_patch_cell` | 5 | `_format_cell_value` always returns a type, so the branch is never taken |
| `data_only` left out or `None` for the formula workbook | 2 | `False` is openpyxl's default |
| `continue` to `break` when a sheet has no `iter_rows` or no archive part; `and` for `or` on the missing part | 3 | openpyxl cannot reload a file with a chart sheet, and every sheet of a saved file has a part |
| `ZipFile(file_path)` without `"r"`; `xml_declaration` None, False or absent | 4 | `"r"` is the default; `standalone=True` makes lxml write the declaration anyway |

## Not verified
- Windows: mutmut forks and runs on Linux only. The module is pure Python on bytes and lxml, so nothing here depends on the platform.
- A real LibreOffice recalculation: the cached-value test rewrites the file's XML by hand to stand in for it.

## Follow-ups
- #165 closes with the per-module numbers once this is merged.
