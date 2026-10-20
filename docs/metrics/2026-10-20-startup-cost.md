# Startup and idle cost of the Python server (#478, part 0)

What this is: how long `coscribe-web` takes to answer its first request, how much memory it
holds a minute later with no conversation open, and where the import time and memory go.
Taken with `office-agent/scripts/measure_startup.py` (the script is the method; every number
below can be re-taken with the commands listed).

## How it was taken

- Machine: cloud container, Linux 6.18, 4 vCPU Intel Xeon @ 2.10 GHz, 16 GB RAM, Python 3.13.16.
  Linux, not Windows: a Windows number needs the Windows runner (see "Not verified").
- Cold start = time from spawning the process to the first successful `GET /` (a stub
  `index.html` stands in for the built frontend, which is static bytes and not Python cost).
  Each run has a fresh HOME and workspace and a fake API key, so the real app starts (not the
  first-run setup page). Five runs, median and range. The OS file cache is warm; there is no
  way to drop it in a container, so a first launch after install (Defender scan, cold disk)
  will be slower than these numbers on a real machine.
- Idle RSS = resident memory of the process tree 60 s after ready, nothing connected.
- Commands:
  ```bash
  cd office-agent
  python scripts/measure_startup.py                                  # dev server
  python scripts/measure_startup.py --cmd <sidecar>/coscribe-server  # PyInstaller onedir
  python scripts/measure_startup.py --imports                        # import times
  ```
  The sidecar was built with `pyinstaller coscribe-server.spec` (the build step of
  `stage-sidecar.sh` without the frontend and the Electron staging), 223 MB onedir.

## Numbers

| | Ready (median, range of 5) | Idle RSS (60 s after ready) |
|---|---|---|
| Dev server (`python -m coscribe.web.app`) | 1.86 s (1.62 - 2.37) | 133 MiB |
| PyInstaller onedir sidecar | 1.99 s (1.93 - 2.16) | 142 MiB |

`import coscribe.web.app` alone is 1.5 - 1.7 s warm (total of all imports by
`-X importtime`: 1.6 s); the remaining ~0.2 s is building the app and binding the port. The
very first import in a fresh container took 6.4 s (cold file cache): the cold-disk case
costs several times the warm one, and no number here covers it on Windows.

## Where the import time goes (warm, `-X importtime`, top by cumulative time)

| Cumulative | Module |
|---|---|
| 1.73 s | `coscribe.web.app` (everything) |
| 0.55 s | `coscribe.conversation` (`session`) |
| 0.50 s | `coscribe.code_runtime` (pulls in `coscribe.tools`) |
| 0.47 s | `coscribe.tools` |
| 0.34 s | `coscribe.tools.office.pptx` (the engine, `checker`, `compiler`) |
| 0.25 s | `coscribe.web.connector_manager` / `runtime_lg.mcp` (`mcp`, `langchain_mcp_adapters`) |
| 0.24 s | `langchain_core.tracers.*` / `langsmith.run_trees` |
| 0.21 s | `fastapi` |

(Cumulative times nest and overlap; they are not additive. `scripts/measure_startup.py
--imports` prints the 30 slowest and the self time per library.)

Self time per top-level library, one warm run: `coscribe` 258 ms, `mcp` 187 ms, `langsmith`
147 ms, `fastapi` 102 ms, `langgraph_sdk` 95 ms, `langchain_core` 91 ms, `openpyxl` 63 ms,
`langgraph` 57 ms, `pydantic` 55 ms, `pptx` 47 ms, `langchain` 42 ms.

## What only an Office tool needs

Loaded at startup today although only an Office tool uses them: `pptx`, `openpyxl`,
`xlsxwriter`, `PIL`, `lxml`, `markdownify` (and its `bs4`). `docx`, `pdfplumber`,
`pypdfium2`, `reportlab` and `mammoth` are already imported lazily and are not loaded.

- Import time: self time of those libraries is 170 - 185 ms of ~1.6 s (three runs); with the
  `coscribe.tools.office.pptx` subtree's own module bodies the subtree is 250 - 340 ms
  cumulative, i.e. 15 - 20 % of the import.
- Memory: importing them after `fastapi`, `pydantic` and `langchain_core` adds 25 MiB to a
  38 MiB process (lxml + PIL 6 MiB, the other four 20 MiB); 25 of the 133 MiB idle RSS, ~19 %.

## What the numbers say

- Startup is already ~2 s warm and idle RSS ~135 MiB. The Office libraries are a real but
  minority share: roughly 0.2 - 0.3 s and 25 MiB. They are the one cost that is both
  measurable and removable by moving imports (part 1). The largest single costs are the
  LangChain/LangGraph/MCP stack and FastAPI, which the server needs on its first turn
  anyway; none of that is in scope.
- The PyInstaller build is ~7 % slower and 9 MiB larger in RSS than the dev server on the
  same machine; unpacking is not the problem.
- Part 1 is justified at that size (about a tenth of the startup time and a fifth of the idle
  memory) and is done as the next PR with its own before and after. Part 2 (starting the
  sidecar earlier) has no Python number to prove here: its number is the time to a usable
  window, measured in the Electron shell.

## Not verified

- Windows. The script has a Windows branch for the memory reading (working set through
  PowerShell) that no one has run; the Windows cold-start and Defender first-launch costs are
  unmeasured. The Windows runner work is #472.
- A cold file cache on any platform other than the very first import noted above.
- The packaged app (installer plus Electron), only its sidecar.
