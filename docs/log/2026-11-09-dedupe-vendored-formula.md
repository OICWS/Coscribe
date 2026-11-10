# The vendored formula compiler is kept once, not twice (shipped)

Why: the engineering assessment found `_native_svg/svg_to_pptx/native_objects/` carried its own
copy of the LaTeX to OMML compiler that `_native_formula/` already vendors. Both come from the same
upstream directory of `hugohe3/ppt-master`, and the five files were byte-identical, so a fix to one
copy would silently miss the other.

## Shipped
- Removed `formula_ast.py`, `formula_compiler.py`, `formula_omml.py`, `formula_parser.py` and
  `formula_profile.py` from `tools/_native_svg/svg_to_pptx/native_objects/` (4,657 lines). The five
  lines that imported them now import `tools/_native_formula`, which exports the extra names they
  use (`estimate_inline_formula_vertical_extent`, `validate_omml_resource_limits`).
- Provenance: every `_native_*` directory already has a `NOTICE.md` with the upstream repository,
  commit and changes. `_native_svg/NOTICE.md` records the removal as change 6 and drops the five
  files from its list; `_native_formula/NOTICE.md` gains a "Changes from upstream" section and says
  that the emitter uses it, and to re-check that the files still match when either is refreshed.

## Checked
- `cmp` showed all five pairs identical before the removal.
- New `test_an_inline_formula_becomes_native_math_in_the_text_run` (`tests/test_deck_engine.py`)
  compiles a page with an inline formula through the emitter; it fails with the old import once
  the emitter's copy is gone, and no test covered this path before. ruff, `lint-imports` and the pytest
  suite pass; mypy reports the same errors as `main` in this container (none in these packages,
  which mypy excludes).

## Not verified
- A real Windows machine. Block formulas (`native_objects/formula.py`) have no caller in
  coscribe's deck engine, so only their import is checked.
