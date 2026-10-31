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

## Measured on Windows (2026-10-27, the maintainer's machine, 26.8.1)
- `msiexec /a LibreOffice_26.8.1_Win_x86-64.msi /qn TARGETDIR=<folder>` run from a non-elevated
  PowerShell (`whoami /groups` showed Medium Mandatory Level) raised no UAC prompt, logged
  `MainEngineThread is returning 0`, and left `program\soffice.exe` in the folder. The machine
  is an administrator's account, so a standard account under a group policy that blocks
  `msiexec` is not covered.
- The download is 357.5 MB; the unpacked folder is **1,522.9 MB**. Bundling it is out of the
  question, and the install button must say so before it downloads.
- Trimmed in a copy, each step followed by converting a file to PDF: Word after every step,
  PowerPoint from the 678 MB state on, Excel only at the 678 MB and 587 MB states:

  | removed | folder size after |
  |---|---|
  | nothing (copy of the unpack) | 1,524 MB |
  | `share\extensions\dict-*` (spelling dictionaries) | 1,068 MB |
  | `program\resource` folders not starting with `en` (UI translations) | 811 MB |
  | `share\config\images_*` (icon themes) | 739 MB |
  | `share\gallery`, `template`, `wizards`, `autotext`, `xpdfimport`, `help`, `readmes`, `extensions\nlpsolver`, `extensions\wiki-publisher` | 678 MB |
  | `share\registry\res\fcfg_langpack_*` except English | **587 MB** |

  At 587 MB the three formats still convert (Word 471,264, Excel 275,353, PowerPoint 226,968
  bytes of PDF). **`share\config\soffice.cfg` cannot be removed**: without it Word and PowerPoint
  files did not convert (Excel was not tried at that step). The `program` dlls (about 394 MB,
  `mergedlo.dll` alone 145 MB) and the fonts (51 MB) were left alone.
- What the trim costs is not measured: text in a language other than English (fonts, line
  breaking, hyphenation), the layout of any file that used a removed template or gallery
  item, and how the converted PDF compares with the untrimmed one beyond its size.
- `soffice.exe --version` prints `LibreOffice 26.8.1.1` and converted a Word file to a 18 KB PDF
  with no installation. `soffice.exe` is a GUI-subsystem launcher: it returns at once and shows a
  console window for `--version`. coscribe calls `program\soffice.com`, which stays attached,
  prints and waits.
- The first run printed "Could not find platform independent libraries <prefix>", a warning of
  LibreOffice's own Python that did not stop the conversion.

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

Retired wording: "The product does not depend on LibreOffice"
