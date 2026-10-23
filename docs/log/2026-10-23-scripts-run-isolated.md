# Scripts run in the AppContainer where the machine passes the self-test (partly shipped)

Why: issue #560, part 2. Part 1 (#567) built the container, the folder grants and the self-test;
this applies them to every tool that runs model-written code. Decision 0021 supersedes the "no OS
sandbox" part of 0002.

## Shipped
- `run_python_script`, `run_node_script`, `run_background_script` and `run_background_command`
  start in the container on Windows when the self-test passed: the workspace and the
  conversation's read-write folders without delete, the read-only folders (`extra_readable`, now
  passed by `coordinator.py`), and the interpreter's own folders. Network stays on for now.
- A run's scratch folder (script text, `TEMP`) moved from the system temp folder to
  `<state>/script-scratch`, granted once.
- A refused delete, rename or write in a contained run adds a note that names `delete_file` and
  `move_file`. The tool descriptions say what holds in each case (`tests/tool_schemas.txt`).
- The self-test result is also kept in memory per process; a folder whose ACE is already there is
  recorded without walking its tree again.

## Not verified
- A real Windows 11 machine, a standard-user or company laptop, OneDrive folders.
- Where the self-test fails, scripts still run with the folder guard only: fail closed and the
  per-conversation opt-in come with the settings screen (part 3).

## Follow-ups
- `docs/plan.md`, "Next" item 4.
