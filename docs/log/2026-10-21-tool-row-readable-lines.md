# A tool call opens to name: value lines, not JSON (partly shipped)

Why: #505. Opening a tool call in the chat printed its arguments and result as JSON, which the people who use coscribe cannot read.

## Shipped
- `lib/toolFields.ts`: pure `describeArgs` / `describeResult` / `rawJson`. Scalars are plain text, a nested object or list is indented lines, a JSON string result is read as JSON, text that is not JSON stays text. Unit tests in `lib/toolFields.test.ts`.
- `components/chatlog/ToolFields.tsx` draws the lines (name small, muted, monospace; value in the text font, wrapped), a result box of bounded height, and a "Raw" fold with the original JSON.
- `ToolRuns.tsx`: the opened call, the approval card and a resolved approval use them; no `JSON.stringify` is left on the opened path except inside "Raw".

## Not verified
- Not looked at in a browser on Windows; before/after screenshots are in the PR.

## Follow-ups
- #505 part 2: every command as a `$ command` box, the file tools as one human line.
