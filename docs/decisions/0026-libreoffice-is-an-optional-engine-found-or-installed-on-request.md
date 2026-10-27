# 0026: LibreOffice is an optional engine, found or installed on request

Status: accepted (2026-10-27, by the maintainer). Supersedes 0012 in what it forbids: a
product code path may now use LibreOffice, but only as an engine that may be absent. The rest of
0012 stands: IronCalc, resvg, pypdfium2 and Microsoft Office (COM) stay, and nothing breaks
without LibreOffice.

## Context
0012 removed LibreOffice because Windows does not ship it and coscribe's users have Microsoft
Office, so every feature that needed it was silently off. Since then the cost of having no real
layout engine has shown:
- A generated Word file can only be checked for structure, not for how it paginates, so
  details (tables over the page edge, orphan headings) reach the person.
- The reviewer works from rendered pages of our own drawing, which costs many tokens.
- Without Microsoft Office there is no way to preview or convert a Word, Excel or PowerPoint
  file.

The maintainer's reading of other agents: OpenAI's ChatGPT/Codex desktop app was reported
(secondary sources summarising Simon Willison, September 2026, not checked first-hand) to keep
a headless LibreOffice of about 430 MB, with Python, Node.js, Poppler and git, in a local
runtime folder; commenters disagreed whether every install, Windows included, gets it.

## Decision
- **Not bundled.** The installer does not grow. LibreOffice is found, or installed on the
  person's request, never forced.
- **Detection** (`soffice` on PATH, the usual Program Files folders, coscribe's own copy, a path
  the person sets) gives one status: not found, found (version, path), or coscribe's copy.
  It is shown in Settings › Capabilities.
- **Install on request.** A button there downloads the official release from The Document
  Foundation into coscribe's data folder (no administrator rights: the MSI is extracted into
  that folder, not installed system-wide), checks its published SHA-256, and records the
  action in the audit log. Nothing is downloaded unless the person presses it. The version and
  the download address are pinned in code and checked live before each release, not guessed.
- **Where it is used, when present:**
  - render a Word, Excel or PowerPoint file to PDF, then to page images (pypdfium2): the
    preview of any Office file, the reviewer's page images and the page-level check of a
    generated Word file (pagination, tables over the edge, empty pages);
  - conversion between Office formats and PDF.
  Microsoft Office (COM) is preferred when installed, because its layout is Word's own;
  LibreOffice is the next choice, and the engines of 0012 are the floor.
- **Absence is stated, not hidden.** A result that came from a renderer says which one made it
  (LibreOffice's layout differs from Word's); a check that could not run says "not checked
  (needs LibreOffice or Microsoft Office)". It is never reported as a pass and never as the
  model's error. The tool list and the system prompt do not change with the status
  (decision 0001): the status reaches the model in a tool result.
- **Running it.** Headless, one private user profile per run (`-env:UserInstallation`), macros
  off, a timeout that kills the process group (`run_killable`), files only inside the
  conversation's folders. It opens documents the model or a person produced, so it is run with
  the same folder limits as scripts where that isolation is set up (0021).
- LibreOffice stays MPL-2.0: coscribe calls it as a separate program and ships none of its
  code.

## Consequences
- 0012's "checks give the same result on every machine" no longer holds for page-level checks;
  they are extra, labelled with their engine, and the floor checks still run everywhere.
- CI runners have LibreOffice (the session hook installs it), so these paths are tested there;
  the install button and the Windows MSI extraction are tested by the maintainer on Windows
  until the Windows CI job can do it.
- The bundled LibreOffice build seen in other apps lacks some fonts and substitutes them
  silently in exported files (reported): coscribe never writes through LibreOffice, only reads
  and renders with it, so a substituted font changes a preview, not a file.

## Order of work
1. Detection and the Settings card (no behaviour change).
2. Render to PDF and page images; the Word page-level check; the reviewer reads those pages.
3. The install button.
4. Preview and conversion of Office files without Microsoft Office.
