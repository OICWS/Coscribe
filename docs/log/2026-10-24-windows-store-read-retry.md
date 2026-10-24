# Task records are read while Windows replaces them (shipped)

Why: on Windows CI, reading a background task's or sub-agent's JSON record while another thread
replaced it raised `PermissionError`, failing tests at random (seen twice on #591).

## Shipped
- `read_text_with_retry` in `tools/_file_locks.py` waits out the replace, as
  `replace_with_retry` already did for the writer; the background-task and sub-agent stores read
  through it, and the background-task store now replaces with `replace_with_retry`.

## Not verified
- Only that the Windows CI job no longer fails this way; the race isn't reproduced on purpose.
