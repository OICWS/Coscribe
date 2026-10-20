# The server no longer loads openpyxl, xlsxwriter, bs4 and markdownify at startup (partly shipped)

Why: #478 part 1. The startup measurement (`docs/metrics/2026-10-20-startup-cost.md`) put the
Office libraries at about a tenth of the launch time and a fifth of the idle memory.

## Shipped
- `tools/web/websearch.py` imports `bs4` and `markdownify` in the function that reads a page;
  `tools/office/pptx/engine/native.py` imports the chart converter (which pulls in `openpyxl` and
  `xlsxwriter`) in the two functions that use it. No tool schema or behaviour changes.
- `scripts/ratchet.py` has a `startup_imports` metric: which Office libraries importing
  `coscribe.web.app` loads, measured in a fresh interpreter. The baseline is the three still
  loaded (`pptx`, `PIL`, `lxml`); a new one fails `--enforce`. Shown by putting `import openpyxl`
  back at the top of `websearch.py`: `WORSE startup_imports: new  openpyxl = 1`, exit 1.
- `scripts/verify_server_office.py` drives a deck build with a native chart and table, a deck
  read, an Excel write and read, a Word write and read and a web page read through the
  WebSocket with the stub model. Run against the PyInstaller sidecar built from this branch all
  seven checks pass.
- Numbers, same machine, interleaved runs (8 each, warm cache): sidecar ready 2.04 s to 1.84 s,
  dev server 1.69 s to 1.52 s; idle RSS 142 to 130 MiB (sidecar) and 133 to 122 MiB (dev);
  260 fewer modules imported.

## Not verified
- Windows: the numbers and the packaged sidecar there.
- `pptx`, `PIL` and `lxml` are still loaded at startup (about 0.1 s and 13 MiB). The engine
  modules import them at module level, `sections.py` among them, which is another session's
  file; `tools/__init__.py` also re-exports the deck engine eagerly. See the comment on #478.
- No spec change was needed: PyInstaller's analysis follows an `import` inside a function (the
  module list of the built sidecar is identical before and after); only dynamic imports by
  string need a hidden import.

## Follow-ups
- Lazy `pptx`/`PIL`/`lxml` once `sections*.py` may be edited; part 2 of #478.
