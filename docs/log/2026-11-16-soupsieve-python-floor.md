# Python floor 3.11.5, so the lock holds only the patched soupsieve (shipped)

Why: Dependabot alerts #78, #79 and #80 (two high, one moderate) on soupsieve 2.10 in
`office-agent/uv.lock`. soupsieve, which beautifulsoup4 pulls in, is fixed in 4.0, and 3.0 and
later need Python 3.11.5. With `requires-python = ">=3.11"` uv kept a second, vulnerable 2.10 for
Python 3.11.0 to 3.11.4.

## Shipped
- `office-agent/pyproject.toml`: `requires-python = ">=3.11.5"`; `uv.lock` re-locked with uv
  0.13.7 (CI's), which drops soupsieve 2.10. Nothing else in the lock changed.
- CI's `python-version: "3.11"` installs the newest 3.11 release, so no workflow changes.

## Not verified
- A Windows machine with an old 3.11.0 to 3.11.4 install: `uv sync` there now asks for a newer
  Python, as intended.

## Follow-ups
- Dependabot alert #77 (minimatch, through electron-builder, build-time only) stays open: the
  newest electron-builder still requires minimatch 10, and forcing 11 with npm `overrides` risks
  the installer build. Revisit when electron-builder moves to minimatch 11.
