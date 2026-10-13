# Vendored SVG-element -> DrawingML emitter

Copied from [`hugohe3/ppt-master`](https://github.com/hugohe3/ppt-master), commit
`bf89859cbf3c5f5974de70e0dd2ccf2239c8c51b` (2026-10-13), from `skills/ppt-master/scripts/`:
the import closure of `svg_to_pptx/drawingml/elements.py` (37 modules, about 24k lines),
including the imports made inside functions, plus the three pre-passes upstream's converter runs
before it (`svg_to_pptx/tspan_flattener.py` with `svg_finalize/flatten_tspan.py` for text lines,
`svg_to_pptx/geometry_properties.py`). Why this part and nothing else, and how it was
measured: `docs/assessments/2026-10-13-office-route.md` (2.6) and decision 0010.

This copy is ours to maintain: a fixed snapshot, updated only on purpose (re-copy, then diff).
coscribe's own code that walks an SVG page and packages the slides lives in
`tools/office/pptx/engine/`; nothing outside it imports from here.

## Changes from upstream

1. Imports of the upstream scripts directory's top-level modules (`from pptx_shapes import`,
   `from language_tags import`, ...) are rewritten to package-relative imports
   (`from ...pptx_shapes import`): 17 lines, mechanical, so the copy is a package inside
   coscribe instead of a set of top-level modules on `sys.path`.
2. The package `__init__.py` files of `svg_to_pptx/`, `svg_to_pptx/native_objects/`,
   `svg_to_pptx/drawingml/` and `pptx_to_svg/` are empty: upstream they import modules
   outside this copy (the exporter CLI, chart and table objects). `pptx_shapes/__init__.py` is
   unchanged.
3. `svg_finalize/flatten_tspan.py` no longer configures the process's stdout encoding at import
   (three lines for its command-line use, which pulled in upstream's attribution check);
   `svg_to_pptx/tspan_flattener.py` imports it package-relatively instead of editing `sys.path`.
4. Nothing else. Docstrings still show upstream's usage examples with top-level imports.

The upstream project checks its own attribution (SKILL.md metadata, LICENSE, SPONSORS) at its
script entry points; none of those entry points is in this copy. The MIT licence below is kept
as it requires.

`pptx_shapes/data/` carries its own provenance (`pptx_shapes/data/NOTICE.md`): DrawingML
preset geometry from Apache POI (Apache-2.0) and the shape type list from the Open XML SDK (MIT).
`svg_to_pptx/drawingml/font_metrics.json` and `font_advances.json` are numeric font metrics
measured by upstream from Office for Mac fonts.

## Files

- `hyperlink_contract.py`
- `language_tags.py`
- `pptx_effects.py`
- `pptx_gradients.py`
- `pptx_shapes/errors.py`
- `pptx_shapes/formula.py`
- `pptx_shapes/loader.py`
- `pptx_shapes/models.py`
- `pptx_shapes/registry.py`
- `pptx_shapes/semantic_hash.py`
- `pptx_shapes/semantics.py`
- `pptx_shapes/xml_safety.py`
- `pptx_to_svg/emu_units.py`
- `pptx_to_svg/preset_authoring.py`
- `pptx_to_svg/preset_registry_to_svg.py`
- `pptx_to_svg/preset_svg_markup.py`
- `resource_paths.py`
- `slide_roster.py`
- `svg_finalize/flatten_tspan.py`
- `svg_to_pptx/drawingml/context.py`
- `svg_to_pptx/drawingml/elements.py`
- `svg_to_pptx/drawingml/hyperlinks.py`
- `svg_to_pptx/drawingml/paths.py`
- `svg_to_pptx/drawingml/styles.py`
- `svg_to_pptx/drawingml/text_baseline.py`
- `svg_to_pptx/drawingml/text_properties.py`
- `svg_to_pptx/drawingml/theme_colors.py`
- `svg_to_pptx/drawingml/theme_fonts.py`
- `svg_to_pptx/drawingml/utils.py`
- `svg_to_pptx/geometry_properties.py`
- `svg_to_pptx/native_objects/formula_ast.py`
- `svg_to_pptx/native_objects/formula_compiler.py`
- `svg_to_pptx/native_objects/formula_omml.py`
- `svg_to_pptx/native_objects/formula_parser.py`
- `svg_to_pptx/native_objects/formula_profile.py`
- `svg_to_pptx/native_objects/formula_run_properties.py`
- `svg_to_pptx/native_objects/inline_formula.py`
- `svg_to_pptx/native_objects/marker_attributes.py`
- `svg_to_pptx/tspan_flattener.py`

## License

MIT License

Copyright (c) 2025-2026 Hugo He

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
