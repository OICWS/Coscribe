# Inline code in the chat is the Settings blue; no line counts on file rows (shipped)

Why: inline code in replies was red (`--code-fg: #b4382b`), out of step with the app's blue
accent, and the "+N -M" line counts on file rows (write_file, edit_file) told the person nothing
they used.

## Shipped
- `--code-fg` is `var(--accent)` in both themes, the blue of the Settings buttons
  (`frontend/src/index.css`), with no grey box behind it: a reply's inline code is only the
  blue monospace text, at the size of the sentence around it (typography's `prose-sm` had it at
  12px against 14px). Code blocks keep their background.
- File rows no longer show "+N -M": `SummaryLabel` drops it and `SummaryParts.diffStat` is gone
  (`frontend/src/lib/transcriptGrouping.ts`). The tools still return `lines_added` /
  `lines_removed`, which the model reads.
- Checked live with DeepSeek (deepseek-flash): an edit_file turn shows "Edited todo.txt" with no
  counts and the reply's inline code in blue.

## Not verified
- On Windows in the desktop app; the dark theme by eye.
