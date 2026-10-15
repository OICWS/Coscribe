# Task file saves retry a refused replace on Windows

The Windows nightly of 2026-10-14 failed once (#267): `os.replace` in `TaskToolkit._save` raised
`PermissionError` while concurrent `task_create` calls saved the thread's task file. Something
else (a scanner or indexer) briefly held the target, which Windows reports as access denied even
under our file lock. `replace_with_retry` in `tools/_file_locks.py` retries up to five times with a
short sleep on Windows only; `tasks.py` uses it. Other atomic writers have the same shape and
were left alone.
