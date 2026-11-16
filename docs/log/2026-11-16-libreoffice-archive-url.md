# LibreOffice downloads from the archive, so a newer release no longer breaks it (shipped)

Why: the pinned 26.8.1 installer was fetched from `download.documentfoundation.org/libreoffice/stable/`,
which keeps only the current releases. Once a newer one came out the address answered 404, so
"Install LibreOffice" failed for everyone and the Windows LibreOffice check
(`test_coscribes_own_libreoffice_is_downloaded_unpacked_and_converts_each_format`) went red on #909.

## Shipped
- `tools/libreoffice_install.py`: the pin points at the same file in the Document Foundation's
  archive (`downloadarchive.documentfoundation.org/libreoffice/old/26.8.1.1/`), which keeps every
  release. Size and SHA-256 are unchanged, so a different file is still refused.

## Not verified
- The archive address could not be fetched from the cloud session (its proxy refuses the host);
  the Windows `real-windows` job downloads it and checks the hash.
