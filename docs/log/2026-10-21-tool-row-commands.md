# Commands as a `$ command` box, the file tools as one line (shipped)

Why: #505, part 2. After part 1 a call opens to plain lines; commands and the file tools still needed the same calm look.

## Shipped
- `commandOf` / `commandOutput` in `lib/toolFields.ts`: every command-like tool (`run_python_script`, `run_node_script`, `run_code_command`, `run_background_script`, `run_background_command`) is a `$ command` line in a white, wrapped box (`CommandBox`), its output below in wrapped monospace in a box of bounded height (`CommandOutput`), in the approval card, the resolved approval and the opened row. The old code-module-only detail is gone. Stdout and stderr of a script, the code module's `output`, and any other record are all handled.
- `list_files` reads "Listed notes" for a folder; Read/Wrote/Edited already named the file.
- `tests/e2e/tool-rows.spec.ts` (added to `e2e.yml`): an opened call shows plain lines and its JSON only behind "Raw".

## Not verified
- Not run on Windows or in the packaged app; looked at in Chromium against the stub model only.

## Follow-ups
- #506 builds its task card on these rows.
