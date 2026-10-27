# Settings downloads a LibreOffice of coscribe's own on request (shipped; part 2 of decision 0026)

Why: decision 0026 makes LibreOffice an optional engine that most Windows computers do not have.
A button that fetches it, unpacked and without administrator rights, is what makes the engine
usable at all.

## Shipped
- `tools/libreoffice_install.py`: downloads the pinned official 26.8.1 MSI (374,870,016 bytes,
  sha256 `c6298b10…5312`, the file whose signature by the LibreOffice Build Team key
  `C2839ECAD9408FBE9531C3E9F434A1EFAFEEAEA3` verified), unpacks it with `msiexec /a` into a staging
  folder, deletes what a conversion never reads (dictionaries, other languages' interface and
  configuration, icon themes, gallery, templates, help), converts a small Word file to PDF to prove
  the trimmed copy works, and moves it to `<state_dir>/libreoffice/26.8.1` in one rename. A hash
  mismatch, a failed check or too little free space (2.2 GB needed while installing, about
  590 MB afterwards) leaves nothing behind. Older versions go once the new one is in.
- `GET`, `POST` and `DELETE /api/libreoffice`: the download runs in the background and the page
  polls its step and progress; each download and removal is written to the audit log; an
  unexpected failure shows a fixed text, the details go to the server log.
- Settings › Capabilities › LibreOffice: a Download button with the sizes stated first, the step
  and a progress bar while it runs, Remove for coscribe's own copy.
- `tests/test_windows_real.py` downloads for real on the Windows runner, converts a Word, an Excel
  and a PowerPoint file and removes it again; `windows-more-checks.yml` runs when these modules
  change.
- Runs use a profile of their own (`profile_argument`), so a person's LibreOffice settings are
  not touched.

## Not verified
- The download and unpack in the app: the tests fake the unpack. The real one is run only by the
  Windows job above, which is an administrator's runner, and by the maintainer's earlier manual
  unpack and conversion (decision 0026). It was not tried on a standard account or under a policy
  that blocks `msiexec`; policy code 1625 is reported as such.
- The trimmed copy was checked on one Word, one Excel and one PowerPoint file; not on other
  languages.
- The key's fingerprint was confirmed from LibreOffice mailing-list posts, not from a page on
  libreoffice.org.

## Follow-ups
- Next in 0026's order: render to PDF and page images, and the Word page-level check.
- A new LibreOffice release needs new pins (version, size, hash), checked against its signature.
