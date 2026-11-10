# Python dependencies are installed from a lock file (shipped)

Why: `pyproject.toml` holds ranges, so every `pip install -e ".[dev,web]"` resolved afresh. One
real install on Windows got pydantic 2.14.0a1 and every connector failed (the comment above the
pydantic range). CI, the Windows jobs and the desktop sidecar could each test or ship different
versions from one day to the next.

## Shipped
- `office-agent/uv.lock` (156 packages, every platform, with hashes) is the one list of exact
  versions. `pyproject.toml` keeps its ranges; a new `sidecar` dependency group locks PyInstaller.
- `office-agent/scripts/install_locked.py` exports the lock with `uv export --locked` and installs
  it with `pip --require-hashes --no-deps` into the Python that runs it, then coscribe itself
  (editable). It fails when the lock no longer matches `pyproject.toml`.
- Every workflow that installed the project (`office-agent-ci`, `windows`, `windows-checks`,
  `windows-more-checks`, `desktop-build`, `desktop-smoke`, `e2e`, `audit`, `mutation`) now goes
  through it, with uv 0.13.7 from `astral-sh/setup-uv@v7`; the pip cache keys on `uv.lock`.
- `office-agent-desktop/scripts/stage-sidecar.sh` brings the venv to the lock (`--extra web --group
  sidecar`) before PyInstaller runs, so a sidecar built on a dev box matches CI. The desktop build
  no longer installs the `dev` extra into that venv; the PyInstaller spec collects none of it.
- Dependabot uses the `uv` ecosystem with `versioning-strategy: lockfile-only`: one grouped pull
  request a week moves the lock inside the ranges and never rewrites a range.
- `tests/test_locked_installs.py` fails on a workflow or the sidecar script that installs the
  project with pip directly, and (where uv is on PATH) on a lock out of date.

## Not verified
- The Windows jobs and the desktop build were not run on a Windows runner here; the lock carries
  the Windows-only packages (pywin32 and the like) and pip picks them by their markers.
- Dependabot's first `uv` pull request has not run yet.

## Follow-ups
- Whether Dependabot's `lockfile-only` also moves indirect dependencies (`docs/plan.md`).
