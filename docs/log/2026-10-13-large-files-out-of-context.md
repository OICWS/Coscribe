# Large data files kept out of AI context (shipped)

Why: a few tracked files are data that no session should read or search whole; they cost
context and slow reviews (assessment section 2.6). Part of #105, closes #111.

## Shipped
- `.gitattributes`: `linguist-generated=true` for the animation presets JSON, the
  `_ooxml_schemas` `.xsd` files, both `package-lock.json`, `site/index.html` and
  `skill_catalog.json`, so GitHub collapses them in diffs.
- Root `.ignore` (read by ripgrep, so by Claude Code's Grep) for the presets JSON, `*.xsd`,
  `package-lock.json` and `site/index.html`. `skill_catalog.json` and the frozen roadmap stay
  searchable. `rg -u` still finds everything.
- `office-agent/tests/test_file_sizes.py`: a tracked text file over 200 KB must be on the
  allow-list with a reason (today's 8 files); a new one fails with what to do. A stale
  allow-list entry fails too.

## Not verified
- GitHub's diff collapsing is only visible on the PR page after it is opened.

## Follow-ups
- Splitting `presentations.py` and its test file would let two entries leave the allow-list.
