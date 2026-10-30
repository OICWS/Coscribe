# The living documents say what is true now, and a test keeps them so (shipped)

Why: the maintainer found `SECURITY.md` still saying "There is no sandbox" a week after scripts
began to run in an AppContainer (decision 0021). For AI sessions that maintain the project, a stale
document is worse than none: they act on it. A pass over the documents found more of the same,
and nothing had failed for any of it.

## Shipped
- Fixed what decisions had overturned: the sandbox in `SECURITY.md`, `docs/security/*`,
  `ARCHITECTURE.md` (and its section title) and the runtime_lg card (0021, 0022); LibreOffice as an
  optional engine (0026); the artifacts and the Artifacts page (0015, 0025, 0027); the built-in
  skills; licensed image search; the code module's commands (refused without the command sandbox,
  Settings › Capabilities, no mirror variable).
- `office-agent/README.md`: the Files, Documents and Scripts sections (about 780 lines that copied
  tool parameters, and described tools since removed: `write_xlsx`, `add_xlsx_chart`,
  `format_xlsx_cells`) are a short section each that says what exists, which skill and decision
  govern it and where the detail lives (the tool's docstring, `tests/tool_schemas.txt`, the card).
  `office-agent/frontend/README.md`, a history of the rewrite (it still called the generated wire
  types hand-encoded), is a short current guide.
- Decision records: 0011, 0014, 0019 and 0021 now name the records that superseded, narrowed or
  changed them, in their status and in the index; 0021 and 0026 list the wording they retired.
- `tests/test_doc_freshness.py`: a code name in backticks in a living document must still be a word
  of the code; wording a decision retired must be gone; a supersession must show on both records
  and in the index. On its first run it found the frontend README's four removed events and the
  0011/0012 and 0021/0022 pairs above.
- `AGENTS.md` and the decisions index: documents name, not copy, a tool's parameters; a superseding
  decision marks the old one and lists retired wording.

## Not verified
- The test catches names that are gone and wording a decision lists; a sentence that is wrong in
  other words still needs a reader. The README sections not rewritten here (browser, MCP, hooks,
  Web UI, desktop) were only checked for names that no longer exist.

## Follow-ups
- Decisions 0010, 0022 and 0028 are still "proposed" though 0010 and 0022 are built and named as
  invariants: the maintainer to accept or change them.
- The rest of `office-agent/README.md` the same way: what exists and where to read more.
