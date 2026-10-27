# Settings › Capabilities shows whether a LibreOffice is on this computer (shipped; part 1 of decision 0026)

Why: decision 0026 makes LibreOffice an optional engine. Before anything uses it, the app has to
know whether one is there.

## Shipped
- `tools/libreoffice.py`: `find_libreoffice` looks for coscribe's own copy first
  (`<state_dir>/libreoffice/<version>/program/`, nothing puts one there yet), then `soffice` or
  `libreoffice` on PATH and the Windows Program Files folders. On Windows it prefers `soffice.com`,
  which prints and waits, over the GUI launcher `soffice.exe`. `libreoffice_status` adds the
  version that `--version` reports (30 s limit, cached by path and modification time).
- `GET /api/libreoffice` and a LibreOffice row and section in Settings › Capabilities: "Not
  found" with a line saying it is optional, or the version, the path and whose copy it is.
- Nothing else changes: no tool, prompt or check reads it yet.

## Not verified
- On Windows: the Program Files lookup and `soffice.com --version` are written from the
  measurements in decision 0026, not run by a test (the tests use shell-script launchers and run on
  Linux only).
- The card in the app: build, lint and the fast checks only, no browser.

## Follow-ups
- Next in 0026's order: the install button (download, unpack with `msiexec /a`, trim, move into
  place), then rendering to PDF and page images.
