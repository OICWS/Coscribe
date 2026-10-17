# Import contracts per component (shipped)

Why: issue #348 item 2. Phase 1 made packages explicit but nothing stopped one component from
importing another's internals; `docs/components.md` listed components that no check enforced.

## Shipped
- `components.toml` now drives one import-linter `protected` contract per package (the 7
  top-level packages and `tools.office.{docx,xlsx,pdf,pptx}`, `tools.exec`, `tools.web`,
  `tools.bookkeeping`): a component's submodules may be imported only from inside it. The
  contracts are generated into the last block of `office-agent/pyproject.toml` by
  `scripts/gen_components.py` (the check is in `check.sh` and `tests/test_components_map.py`).
- Today's outside imports into submodules are each component's `ignore_imports` in
  `components.toml`: 39 lines in all (`runtime_lg` 11, `tools` 9, `bookkeeping` 8, `pptx` 4,
  `exec` 4, `pdf` 2, `workflows` 1). An entry that stops matching fails `lint-imports`, so the
  lists can only shrink.
- `tools` lists its protected modules by hand (its loose modules sit beside the sub-components);
  a test fails when a loose module is added and not listed.
- A `layers` contract with `containers = ["coscribe.tools.office"]` and `exhaustive = true`:
  `document_tools` above the four formats (siblings, so independent) above `table_layout` above
  `markdown_blocks | toolkit`. Three ignored imports record real coupling: `pptx` reads `pdf.text`
  in its checker, and `_thumbnail` and `_svg_preview` import the pptx engine, which puts every
  format on a path to `pptx`.
- Every contract, old and new, has `broken_contract_guidance`.
- Shown by breaking: a docx module importing `pptx`, and `conversation` importing `tools.exec.scripts`,
  each fail `lint-imports` with the guidance text.

## Not verified
- The contracts were not run on Windows (import-linter reads source, so the result does not depend on the OS).
- `acyclic_siblings` (assessment §2.5) is not added; no cycle is known.

## Follow-ups
- Shrink the ignore lists: export the names `web`, `runtime_lg` and `conversation` reach for
  (`subagent_tasks`, `background_tasks`, `mcp_oauth`) from their packages.
- A `skills`/templates component for the loose modules left in `tools/`.
