# The command sandbox reads programs from the server's PATH (shipped)

Why: the independent review of #1019 found that the folders the command sandbox may read programs
from came from the command's own `PATH`. A workspace variable could name a private folder there,
and the sandbox would be granted read access to it, which "Hide your private folders from
commands" (decision 0022) promises not to do.

## Shipped
- `start_command` takes the program folders from the server's own `PATH`, never from the
  command's environment. A command still runs with its workspace's `PATH`; a program in a
  hidden private folder that only that `PATH` names is not readable in the sandbox.

## Not verified
- On Windows with the sandbox set up; checked by `tests/test_command_sandbox.py`.
