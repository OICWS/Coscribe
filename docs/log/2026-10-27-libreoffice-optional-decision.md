# LibreOffice becomes an optional engine, found or installed on request (decision only)

Why: Word files could only be checked for structure, the reviewer costs many tokens on pages we
draw ourselves, and without Microsoft Office a Word or Excel file has no preview. The maintainer
decided to overturn 0012.

## Shipped
- Decision 0026: not bundled; detected or installed on request; used for page rendering, the
  Word page-level check and conversion when present; Microsoft Office stays first and the
  engines of 0012 stay as the floor. 0012 is marked superseded in what it forbids.

## Not verified
- That the Document Foundation's MSI can be extracted without administrator rights on a clean
  Windows machine, and the download address and checksum: both are checked when the install
  button is built.
- The report that ChatGPT/Codex bundles LibreOffice (about 430 MB): only secondary sources.

## Follow-ups
- Build in the order of 0026; tracked in `docs/plan.md`.
