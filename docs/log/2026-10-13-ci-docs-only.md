# A documentation-only pull request runs the documentation tests, not the whole CI (shipped)

Why: a pull request that only changed a report waited 10+ minutes for the full CI run, and the run
grows with the code.

## Shipped
- The `test` job decides its scope first (`office-agent/scripts/ci_scope.py`, on the files the pull
  request changes): when every file is documentation (`docs/`, Markdown at the root or at the top
  of `office-agent/`, the package cards), it runs only the documentation tests (references, layout,
  file sizes, module cards) and still reports, since `test` is a required check. Markdown the
  product reads (a skill's SKILL.md) is not documentation. Pushes to `main` always run everything.
- `tests/test_ci_scope.py` pins which files count; widening the rule to every Markdown file makes
  three of its cases fail.

## Not verified
- The documentation path runs for the first time on the next documentation-only pull request; this
  one changes code, so it ran the full CI.
