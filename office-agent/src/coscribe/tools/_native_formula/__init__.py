"""Vendored LaTeX -> OMML (Office Math Markup Language) compiler -- see
``NOTICE.md`` in this directory for exact provenance. The names below are the
ones meant to be called from outside this package: ``tools/presentations.py``
uses the two compile functions, and the vendored SVG emitter
(``_native_svg/svg_to_pptx/``) uses all of them, because upstream ships the
same five files inside that emitter and coscribe keeps one copy here.
Everything else is this compiler's own internal AST/parser/serializer
plumbing.
"""

from __future__ import annotations

from .formula_compiler import (
    FormulaCompileError,
    compile_latex_to_inline_omml,
    compile_latex_to_omml,
    estimate_inline_formula_vertical_extent,
)
from .formula_omml import validate_omml_resource_limits

__all__ = [
    "FormulaCompileError",
    "compile_latex_to_inline_omml",
    "compile_latex_to_omml",
    "estimate_inline_formula_vertical_extent",
    "validate_omml_resource_limits",
]
