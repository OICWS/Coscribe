# LibreOffice becomes an optional engine, found or installed on request (decision only)

Why: Word files could only be checked for structure, the reviewer costs many tokens on pages we
draw ourselves, and without Microsoft Office a Word or Excel file has no preview. The maintainer
decided to overturn 0012.

## Shipped
- Decision 0026: not bundled; detected or installed on request; used for page rendering, the
  Word page-level check and conversion when present; Microsoft Office stays first and the
  engines of 0012 stay as the floor. 0012 is marked superseded in what it forbids.

## Not verified
- The unpack without elevation was tried once, on an administrator's account in a non-elevated
  shell (no UAC, Word to PDF worked, 1.5 GB unpacked). Not tried on a standard account or under
  a policy that blocks `msiexec`.
- The checksum and what can be removed from the 1.5 GB: checked when the install button is built.
- The report that ChatGPT/Codex bundles LibreOffice (about 430 MB): only secondary sources.

## Follow-ups
- Build in the order of 0026; tracked in `docs/plan.md`.
