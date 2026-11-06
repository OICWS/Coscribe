# A turn that wrote an Office file which doesn't open hears it before it ends (shipped)

Why: step 4 of #819. The worst way for a turn to end is a reply that says the file is ready when Word can't open it. The person finds out later, and has to say "the file is broken".

## Shipped
- `runtime_lg/delivery_check.py` collects the `.docx`, `.xlsx` and `.pptx` files this turn wrote. These are the paths named by writing calls (`WRITE_LOCAL` tools, also through `use_tool`) and the files a script reported in its result's `files_written`.
- It opens each one the way the office libraries do: the zip and its CRCs, then python-docx, openpyxl (read-only) or python-pptx. It also names the error.
- `turn_checks.py`: the turn-end check now sends back both open tasks and files that don't open, in one note, once per turn. Like the plan check, the note is not shown in the chat and does not start a turn.
- A file that doesn't exist, or a path outside the workspace, is skipped. The check only covers what was written.

## Not verified
- On deepseek-flash, the multi-turn evaluation passes every task on `main`, so this step can't show a gain there. The check is covered by tests with a scripted model that writes a text file named `.docx`.
- A real Windows run. The check uses only Python libraries that are already dependencies.

## Follow-ups
- A file that opens but is wrong (an empty sheet, a slide with text off the page) is not caught. The design and render checks the deck skills already run cover part of that.
