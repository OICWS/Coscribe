# A write does not use a copy the person has since edited

Why: the person edits a Word, Excel or PowerPoint file in the app while coscribe works on it. Until now coscribe was told of those edits once, at the start of its next turn, and a write tool read the file at call time but never checked that it was the file the model had read. A turn that read a document, waited on a long step and then wrote could write from a copy older than the person's edit.

## Shipped
- `runtime_lg/edit_guard.py`: a tool-call middleware. After any tool that takes a `path` to a `.docx`, `.pptx` or `.xlsx` it remembers the file's hash; before a tool of risk `WRITE_LOCAL` it compares. If the file differs (the person saved in the app meanwhile) the write is not made and the result says the person changed the file after the model last read it, to read it again and repeat the change on what it reads. The model's own writes are remembered as they happen, so they are not taken for the person's.
- `build_langgraph_agent(resolve_file=...)`; the session passes its workspace scope. No tool schema, prompt or system-prompt change (decision 0001): the news is a tool result.
- Unit tests for the guard and one through a real graph.

## Not verified
- Not run with a real model or on Windows. A file never read in this conversation is not guarded (the note at the start of the turn covers that case), and so is a file the person changes between the guard's check and the tool's write, a window of milliseconds.
- The approval card is shown before the check, so in a manual mode the person may approve a write that is then refused.

## Follow-ups
- The editor side: save what the person typed while a turn runs at once, and on a conflict keep their unsaved text instead of offering only Reload.
