# Doc artifact, step 1: the format, blocks with line ranges, block-level edits

Date: 2026-10-26
Area: tools

Step 1 of decision 0025. `tools/office/doc` reads a markdown file marked `coscribe: doc` in its
front matter as blocks (heading, paragraph, list, table, quote, call-out, chart, code, rule, html,
other), each with the lines it covers, from markdown-it-py's block ranges. `apply_edits` replaces,
inserts and deletes whole blocks by index and rewrites only those lines: every other line, and the
file's own line endings, stay byte for byte; a replace or delete that carries text different from
the block's current text is refused and nothing is written. A call-out is a quote opened with a
GitHub alert line (`[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]` or `[!CAUTION]`; the design named
four, GitHub has five and a model writes all of them). A chart is a fenced `chart` block, a kind and
an optional title, then a pipe table; `parse_chart` reads it with the code Word charts use.

A property test found that markdown-it counts the blank lines after a list in the list's range, so
a replace swallowed the blank line; block ranges now stop at the last non-blank line.

`markdown-it-py` is now a declared dependency. Nothing in the app calls the package yet.

Not verified: that models write the two additions unprompted (step 6 measures it); a very large
file (nothing limits it yet).
